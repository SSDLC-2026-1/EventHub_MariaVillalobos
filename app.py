from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional
import json

from flask import Flask, abort, redirect, render_template, request, session, url_for

from auth_validation import (
    validate_login_form,
    validate_profile_form,
    validate_register_form,
)
from encryption import decrypt_aes, encrypt_aes, hash_password, verify_password
from validation import validate_payment_form

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = "dev-secret-change-me"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EVENTS_PATH = DATA_DIR / "events.json"
USERS_PATH = DATA_DIR / "users.json"
ORDERS_PATH = DATA_DIR / "orders.json"

CATEGORIES = ["All", "Music", "Tech", "Sports", "Business"]
CITIES = ["Any", "New York", "San Francisco", "Berlin", "London", "Oakland", "San Jose"]

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_SECONDS = 30
SESSION_TIMEOUT_SECONDS = 180
LOGIN_ATTEMPTS: Dict[str, Dict[str, int | float]] = {}
AES_KEY = b"eventhub-lab-key"


@dataclass(frozen=True)
class Event:
    id: int
    title: str
    category: str
    city: str
    venue: str
    start: datetime
    end: datetime
    price_usd: float
    available_tickets: int
    banner_url: str
    description: str


def ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for path in (EVENTS_PATH, USERS_PATH, ORDERS_PATH):
        if not path.exists():
            path.write_text("[]", encoding="utf-8")


def _user_with_defaults(u: dict) -> dict:
    u = dict(u)
    u.setdefault("role", "user")
    u.setdefault("status", "active")
    u.setdefault("locked_until", "")
    return u


def _parse_iso_datetime(value: str | None) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _now_utc() -> datetime:
    return datetime.utcnow()


def _is_locked(user: dict) -> tuple[bool, int]:
    locked_until = _parse_iso_datetime(user.get("locked_until"))
    if not locked_until:
        return False, 0
    remaining = int((locked_until - _now_utc()).total_seconds())
    if remaining <= 0:
        return False, 0
    return True, remaining


def _clear_lock_for_user(email: str) -> None:
    email_norm = (email or "").strip().lower()
    LOGIN_ATTEMPTS[email_norm] = {"attempts": 0, "lockout_until": 0}

    users = load_users()
    changed = False
    for u in users:
        if (u.get("email") or "").strip().lower() == email_norm:
            if u.get("locked_until"):
                u["locked_until"] = ""
                changed = True
            break
    if changed:
        save_users(users)


def _register_failed_login(email: str) -> tuple[int, bool]:
    email_norm = (email or "").strip().lower()
    state = LOGIN_ATTEMPTS.setdefault(email_norm, {"attempts": 0, "lockout_until": 0})
    state["attempts"] = int(state.get("attempts", 0)) + 1

    users = load_users()
    lock_applied = False
    if state["attempts"] >= MAX_FAILED_ATTEMPTS:
        lockout_until = _now_utc() + timedelta(seconds=LOCKOUT_SECONDS)
        state["lockout_until"] = int(lockout_until.timestamp())
        for u in users:
            if (u.get("email") or "").strip().lower() == email_norm:
                u["locked_until"] = lockout_until.isoformat()
                lock_applied = True
                break
        save_users(users)
    return int(state["attempts"]), lock_applied


def _decrypt_phone(user: dict) -> str:
    phone_data = user.get("phone_encrypted")
    if isinstance(phone_data, dict):
        try:
            return decrypt_aes(
                phone_data["ciphertext"],
                phone_data["nonce"],
                phone_data["tag"],
                AES_KEY,
            )
        except Exception:
            return ""
    return (user.get("phone") or "").strip()


def _encrypt_field(value: str) -> dict:
    ciphertext, nonce, tag = encrypt_aes(value, AES_KEY)
    return {"ciphertext": ciphertext, "nonce": nonce, "tag": tag}


def _verify_user_password(user: dict, password: str) -> bool:
    if isinstance(user.get("password_data"), dict):
        return verify_password(password, user["password_data"])

    legacy_password = user.get("password")
    if legacy_password and legacy_password == password:
        users = load_users()
        email_norm = (user.get("email") or "").strip().lower()
        for u in users:
            if (u.get("email") or "").strip().lower() == email_norm:
                u.pop("password", None)
                u["password_data"] = hash_password(password)
                save_users(users)
                break
        return True
    return False


def _migrate_old_orders() -> None:
    orders = load_orders()
    changed = False
    for order in orders:
        payment = order.get("payment") or {}
        if not isinstance(payment, dict):
            continue

        payment.pop("cvv", None)
        payment.pop("card_number", None)

        if "card" in payment and payment.get("card"):
            card = payment.pop("card")
            last4 = str(card)[-4:]
            payment["card_masked"] = f"**** **** **** {last4}"
            changed = True

        if "billing_email" in payment and payment.get("billing_email") and not payment.get("billing_email_encrypted"):
            payment["billing_email_encrypted"] = _encrypt_field(payment.pop("billing_email"))
            changed = True

        order["payment"] = payment
    if changed:
        save_orders(orders)


def load_events() -> List[Event]:
    ensure_data_files()
    data = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    return [
        Event(
            id=int(e["id"]),
            title=e["title"],
            category=e["category"],
            city=e["city"],
            venue=e["venue"],
            start=datetime.fromisoformat(e["start"]),
            end=datetime.fromisoformat(e["end"]),
            price_usd=float(e["price_usd"]),
            available_tickets=int(e["available_tickets"]),
            banner_url=e.get("banner_url", ""),
            description=e.get("description", ""),
        )
        for e in data
    ]


def _parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def _safe_int(value: str, default: int = 1, min_v: int = 1, max_v: int = 10) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_v, min(max_v, n))


def filter_events(q: str = "", city: str = "Any", date: Optional[datetime] = None, category: str = "All") -> List[Event]:
    q_norm = (q or "").strip().lower()
    city_norm = (city or "Any").strip()
    category_norm = (category or "All").strip()

    results = load_events()

    if category_norm != "All":
        results = [e for e in results if e.category == category_norm]
    if city_norm != "Any":
        results = [e for e in results if e.city == city_norm]
    if date:
        results = [e for e in results if e.start.date() == date.date()]
    if q_norm:
        results = [e for e in results if q_norm in e.title.lower() or q_norm in e.venue.lower()]

    results.sort(key=lambda e: e.start)
    return results


def get_event_or_404(event_id: int) -> Event:
    for e in load_events():
        if e.id == event_id:
            return e
    abort(404)


def load_users() -> list[dict]:
    ensure_data_files()
    return json.loads(USERS_PATH.read_text(encoding="utf-8"))


def save_users(users: list[dict]) -> None:
    ensure_data_files()
    USERS_PATH.write_text(json.dumps(users, indent=2), encoding="utf-8")


def find_user_by_email(email: str) -> Optional[dict]:
    users = load_users()
    email_norm = (email or "").strip().lower()
    for u in users:
        if (u.get("email", "") or "").strip().lower() == email_norm:
            return _user_with_defaults(u)
    return None


def user_exists(email: str) -> bool:
    return find_user_by_email(email) is not None


def load_orders() -> list[dict]:
    ensure_data_files()
    return json.loads(ORDERS_PATH.read_text(encoding="utf-8"))


def save_orders(orders: list[dict]) -> None:
    ensure_data_files()
    ORDERS_PATH.write_text(json.dumps(orders, indent=2), encoding="utf-8")


def next_order_id(orders: list[dict]) -> int:
    return max([o.get("id", 0) for o in orders], default=0) + 1


def get_current_user() -> Optional[dict]:
    email = session.get("user_email")
    if not email:
        return None
    return find_user_by_email(email)


def _is_session_expired() -> bool:
    last_seen_raw = session.get("last_seen_at")
    last_seen = _parse_iso_datetime(last_seen_raw)
    if not last_seen:
        return True
    return (_now_utc() - last_seen).total_seconds() > SESSION_TIMEOUT_SECONDS


def require_login(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_email"):
            return redirect(url_for("login", next=request.path))
        if _is_session_expired():
            session.clear()
            return redirect(url_for("login", expired="1"))
        session["last_seen_at"] = _now_utc().isoformat()
        return view_func(*args, **kwargs)
    return wrapper


def require_role(role_name: str):
    def decorator(view_func):
        @wraps(view_func)
        @require_login
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user or (user.get("role") or "user").lower() != role_name.lower():
                return render_template("403.html"), 403
            return view_func(*args, **kwargs)
        return wrapper
    return decorator


@app.context_processor
def inject_nav_context():
    current_user = get_current_user()
    return {
        "current_user": current_user,
        "is_authenticated": bool(current_user),
        "is_admin": bool(current_user and (current_user.get("role") or "").lower() == "admin"),
    }


@app.get("/")
def index():
    q = request.args.get("q", "")
    city = request.args.get("city", "Any")
    date_str = request.args.get("date", "")
    category = request.args.get("category", "All")

    date = _parse_date(date_str)
    events = filter_events(q=q, city=city, date=date, category=category)

    return render_template(
        "index.html",
        q=q,
        city=city,
        date_str=date_str,
        category=category,
        categories=CATEGORIES,
        cities=CITIES,
        featured=events[:3],
        upcoming=events[:6],
    )


@app.get("/event/<int:event_id>")
def event_detail(event_id: int):
    event = get_event_or_404(event_id)
    similar = [e for e in load_events() if e.category == event.category and e.id != event.id][:5]
    return render_template("event_detail.html", event=event, similar=similar)


@app.post("/event/<int:event_id>/buy")
def buy_ticket(event_id: int):
    event = get_event_or_404(event_id)
    qty = _safe_int(request.form.get("qty", "1"), default=1, min_v=1, max_v=8)

    if qty > event.available_tickets:
        similar = [e for e in load_events() if e.category == event.category and e.id != event.id][:5]
        return render_template(
            "event_detail.html",
            event=event,
            similar=similar,
            buy_error="Not enough tickets available for that quantity.",
        ), 400

    return redirect(url_for("checkout", event_id=event.id, qty=qty))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        registered = request.args.get("registered")
        expired = request.args.get("expired")
        info_message = None
        if registered == "1":
            info_message = "Account created successfully. Please sign in."
        elif expired == "1":
            info_message = "Your session expired after 3 minutes of inactivity. Please sign in again."
        return render_template("login.html", info_message=info_message, field_errors={}, form={"email": ""})

    email = request.form.get("email", "")
    password = request.form.get("password", "")
    clean, field_errors = validate_login_form(email=email, password=password)

    if field_errors:
        return render_template(
            "login.html",
            error="Please fix the highlighted fields.",
            field_errors=field_errors,
            form={"email": clean.get("email", email)},
        ), 400

    user = find_user_by_email(clean["email"])
    if user:
        locked, seconds_left = _is_locked(user)
        if locked:
            minutes_left = max(1, (seconds_left + 59) // 60)
            return render_template(
                "login.html",
                error=f"This account is temporarily locked. Try again in about {minutes_left} minute(s).",
                field_errors={"email": " ", "password": " "},
                form={"email": clean["email"]},
            ), 401
        elif user.get("locked_until"):
            _clear_lock_for_user(clean["email"])

    if not user or (user.get("status") or "active").lower() != "active" or not _verify_user_password(user, clean["password"]):
        if user:
            attempts, lock_applied = _register_failed_login(clean["email"])
            if lock_applied:
                return render_template(
                    "login.html",
                    error="Invalid credentials. Your account has been temporarily locked for 5 minutes.",
                    field_errors={"email": " ", "password": " "},
                    form={"email": clean["email"]},
                ), 401
        return render_template(
            "login.html",
            error="Invalid credentials.",
            field_errors={"email": " ", "password": " "},
            form={"email": clean["email"]},
        ), 401

    _clear_lock_for_user(clean["email"])
    session.clear()
    session["user_email"] = clean["email"]
    session["login_time"] = _now_utc().isoformat()
    session["last_seen_at"] = _now_utc().isoformat()
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", field_errors={}, form={}, demo_message=None, error=None)

    users = load_users()
    clean, field_errors = validate_register_form(
        full_name=request.form.get("full_name", ""),
        email=request.form.get("email", ""),
        phone=request.form.get("phone", ""),
        password=request.form.get("password", ""),
        confirm_password=request.form.get("confirm_password", ""),
        agree=request.form.get("agree"),
        email_exists_checker=lambda e: any((u.get("email") or "").strip().lower() == e for u in users),
    )

    if field_errors:
        return render_template(
            "register.html",
            field_errors=field_errors,
            form=clean,
            error="Please fix the highlighted fields.",
            demo_message=None,
        ), 400

    next_id = max([u.get("id", 0) for u in users], default=0) + 1
    users.append(
        {
            "id": next_id,
            "full_name": clean["full_name"],
            "email": clean["email"],
            "phone_encrypted": _encrypt_field(clean["phone"]),
            "password_data": hash_password(clean["password"]),
            "role": "user",
            "status": "active",
            "locked_until": "",
        }
    )
    save_users(users)
    return redirect(url_for("login", registered="1"))


@app.get("/logout")
@require_login
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/dashboard")
@require_login
def dashboard():
    paid = request.args.get("paid") == "1"
    user = get_current_user()
    orders = [o for o in load_orders() if (o.get("user_email") or "").strip().lower() == (user.get("email") or "").strip().lower()]
    orders.sort(key=lambda o: o.get("created_at", ""), reverse=True)
    return render_template(
        "dashboard.html",
        user_name=user.get("full_name") or "User",
        paid=paid,
        orders=orders,
    )


@app.route("/checkout/<int:event_id>", methods=["GET", "POST"])
@require_login
def checkout(event_id: int):
    event = get_event_or_404(event_id)
    qty = _safe_int(request.args.get("qty", "1"), default=1, min_v=1, max_v=8)

    if qty > event.available_tickets:
        abort(400)

    service_fee = 5.00
    subtotal = event.price_usd * qty
    total = subtotal + service_fee

    if request.method == "GET":
        return render_template(
            "checkout.html",
            event=event,
            qty=qty,
            subtotal=subtotal,
            service_fee=service_fee,
            total=total,
            errors={},
            form_data={},
        )

    clean, errors = validate_payment_form(
        card_number=request.form.get("card_number", ""),
        exp_date=request.form.get("exp_date", ""),
        cvv=request.form.get("cvv", ""),
        name_on_card=request.form.get("name_on_card", ""),
        billing_email=request.form.get("billing_email", ""),
    )

    form_data = {
        "exp_date": clean.get("exp_date", ""),
        "name_on_card": clean.get("name_on_card", ""),
        "billing_email": clean.get("billing_email", ""),
        "card_last4": clean.get("card_last4", ""),
    }

    if errors:
        return render_template(
            "checkout.html",
            event=event,
            qty=qty,
            subtotal=subtotal,
            service_fee=service_fee,
            total=total,
            errors=errors,
            form_data=form_data,
        ), 400

    orders = load_orders()
    order_id = next_order_id(orders)
    current_user = get_current_user()
    orders.append(
        {
            "id": order_id,
            "user_email": (current_user.get("email") or "").strip().lower(),
            "event_id": event.id,
            "event_title": event.title,
            "qty": qty,
            "unit_price": event.price_usd,
            "service_fee": service_fee,
            "total": total,
            "status": "PAID",
            "created_at": _now_utc().isoformat(),
            "payment": {
                "exp_date": clean.get("exp_date", ""),
                "name_on_card": clean.get("name_on_card", ""),
                "billing_email_encrypted": _encrypt_field(clean.get("billing_email", "")),
                "card_masked": f"**** **** **** {clean.get('card_last4', '')}",
            },
        }
    )
    save_orders(orders)
    return redirect(url_for("dashboard", paid="1"))


@app.route("/profile", methods=["GET", "POST"])
@require_login
def profile():
    user = get_current_user()
    form = {
        "full_name": user.get("full_name", ""),
        "email": user.get("email", ""),
        "phone": _decrypt_phone(user),
    }
    field_errors: dict[str, str] = {}
    success_msg = None

    if request.method == "POST":
        users = load_users()
        clean, field_errors = validate_profile_form(
            full_name=request.form.get("full_name", ""),
            phone=request.form.get("phone", ""),
            current_password=request.form.get("current_password", ""),
            new_password=request.form.get("new_password", ""),
            confirm_new_password=request.form.get("confirm_new_password", ""),
            password_verifier=lambda current_password: _verify_user_password(user, current_password),
            user_email=(user.get("email") or "").strip().lower(),
        )

        form.update({
            "full_name": clean.get("full_name", ""),
            "email": user.get("email", ""),
            "phone": clean.get("phone", ""),
        })

        if not field_errors:
            email_norm = (user.get("email") or "").strip().lower()
            for u in users:
                if (u.get("email") or "").strip().lower() == email_norm:
                    u["full_name"] = clean["full_name"]
                    u["phone_encrypted"] = _encrypt_field(clean["phone"])
                    u.pop("phone", None)
                    if clean.get("new_password"):
                        u.pop("password", None)
                        u["password_data"] = hash_password(clean["new_password"])
                    break
            save_users(users)
            success_msg = "Profile updated successfully."

    return render_template(
        "profile.html",
        form=form,
        field_errors=field_errors,
        success_message=success_msg,
    )


@app.get("/admin/users")
@require_role("admin")
def admin_users():
    q = (request.args.get("q") or "").strip().lower()
    role = (request.args.get("role") or "all").strip().lower()
    status = (request.args.get("status") or "all").strip().lower()
    lockout = (request.args.get("lockout") or "all").strip().lower()

    users = []
    for raw in load_users():
        u = _user_with_defaults(raw)
        u["phone"] = _decrypt_phone(u)
        users.append(u)

    if q:
        users = [u for u in users if q in (u.get("full_name", "").lower()) or q in (u.get("email", "").lower())]
    if role != "all":
        users = [u for u in users if (u.get("role", "user").lower() == role)]
    if status != "all":
        users = [u for u in users if (u.get("status", "active").lower() == status)]
    if lockout != "all":
        if lockout == "locked":
            users = [u for u in users if _is_locked(u)[0]]
        elif lockout == "not_locked":
            users = [u for u in users if not _is_locked(u)[0]]

    users.sort(key=lambda u: (u.get("full_name", "").lower(), u.get("id", 0)))
    return render_template(
        "admin_users.html",
        users=users,
        filters={"q": q, "role": role, "status": status, "lockout": lockout},
        total=len(users),
    )


@app.post("/admin/users/<int:user_id>/toggle")
#@require_role("admin")
def admin_toggle_user(user_id: int):
    users = load_users()
    current_user = get_current_user()
    for u in users:
        if int(u.get("id", 0)) == user_id:
            if (u.get("email") or "").strip().lower() == (current_user.get("email") or "").strip().lower():
                break
            u.setdefault("status", "active")
            u["status"] = "disabled" if u["status"] == "active" else "active"
            break
    save_users(users)
    return redirect(url_for("admin_users"))


@app.post("/admin/users/<int:user_id>/role")
#@require_role("admin")
def admin_change_role(user_id: int):
    new_role = (request.form.get("role", "user") or "user").strip().lower()
    if new_role not in {"user", "admin"}:
        new_role = "user"
    users = load_users()
    current_user = get_current_user()
    for u in users:
        if int(u.get("id", 0)) == user_id:
            if current_user and (u.get("email") or "").strip().lower() == (current_user.get("email") or "").strip().lower() and new_role != "admin":
                break
            u["role"] = new_role
            break
    save_users(users)
    return redirect(url_for("admin_users"))

@app.get("/admin/users/list")
def admin_list_users():
    users = []
    for raw in load_users():
        u = _user_with_defaults(raw)
        users.append({
            "id": u.get("id"),
            "full_name": u.get("full_name"),
            "email": u.get("email"),
            "role": u.get("role", "user"),
            "status": u.get("status", "active"),
        })
    return {"users": users}, 200

@app.errorhandler(403)
def handle_forbidden(_error):
    return render_template("403.html"), 403


ensure_data_files()
_migrate_old_orders()


if __name__ == "__main__":
    app.run(debug=True)
