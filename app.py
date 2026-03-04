from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from functools import wraps

from flask import Flask, render_template, request, abort, url_for, redirect, session, flash
from pathlib import Path
import json

from validation import validate_payment_form
from encryption import hash_password, verify_password, encrypt_sensitive_data, decrypt_sensitive_data

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = "dev-secret-change-me"

# Constante para tiempo de expiración de sesión (3 minutos en segundos)
SESSION_TIMEOUT_SECONDS = 180


BASE_DIR = Path(__file__).resolve().parent
EVENTS_PATH = BASE_DIR / "data" / "events.json"
USERS_PATH = BASE_DIR / "data" / "users.json"
ORDERS_PATH = BASE_DIR / "data" / "orders.json"
CATEGORIES = ["All", "Music", "Tech", "Sports", "Business"]
CITIES = ["Any", "New York", "San Francisco", "Berlin", "London", "Oakland", "San Jose"]


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

def _user_with_defaults(u: dict) -> dict:
    u = dict(u)
    u.setdefault("role", "user")      
    u.setdefault("status", "active")  
    u.setdefault("locked_until", "") 
    return u

def check_session_timeout():
    """
    Verifica si la sesión ha expirado.
    Si ha pasado más de SESSION_TIMEOUT_SECONDS desde el login, invalida la sesión.
    Retorna True si la sesión es válida, False si ha expirado.
    """
    login_time = session.get('login_time')
    
    if not login_time:
        return False
    
    try:
        # Convertir el tiempo de login a datetime si es string
        if isinstance(login_time, str):
            login_time = datetime.fromisoformat(login_time)
        
        # Calcular tiempo transcurrido
        elapsed = (datetime.utcnow() - login_time).total_seconds()
        
        if elapsed > SESSION_TIMEOUT_SECONDS:
            # Sesión expirada - limpiar
            session.clear()
            flash("Your session has expired. Please login again.", "info")
            return False
        
        # Actualizar el tiempo de login para mantener la sesión activa
        session['login_time'] = datetime.utcnow().isoformat()
        return True
        
    except (ValueError, TypeError):
        # Si hay error en el formato, invalidar sesión
        session.clear()
        return False

def login_required(f):
    """
    Decorador para rutas que requieren autenticación.
    Verifica que el usuario esté autenticado y que la sesión no haya expirado.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            # Si no hay usuario o sesión expirada, redirigir al login
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_user() -> Optional[dict]:
    """
    Obtiene el usuario actual si la sesión es válida y no ha expirado.
    Si la sesión ha expirado, retorna None.
    """
    email = session.get("user_email")
    if not email:
        return None
    
    # Verificar timeout de sesión
    if not check_session_timeout():
        return None
    
    return find_user_by_email(email)

def load_events() -> List[Event]:
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


EVENTS: List[Event] = load_events()


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parsea fecha estilo YYYY-MM-DD. Devuelve None si inválida."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def _safe_int(value: str, default: int = 1, min_v: int = 1, max_v: int = 10) -> int:
    """Validación simple de enteros para inputs (cantidad, etc.)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_v, min(max_v, n))


def filter_events(
    q: str = "",
    city: str = "Any",
    date: Optional[datetime] = None,
    category: str = "All",
    ) -> List[Event]:
    q_norm = (q or "").strip().lower()
    city_norm = (city or "Any").strip()
    category_norm = (category or "All").strip()

    results = load_events()

    if category_norm != "All":
        results = [e for e in results if e.category == category_norm]

    if city_norm != "Any":
        results = [e for e in results if e.city == city_norm]

    if date:
        results = [
            e for e in results
            if e.start.date() == date.date()
        ]

    if q_norm:
        results = [
            e for e in results
            if q_norm in e.title.lower() or q_norm in e.venue.lower()
        ]

    results.sort(key=lambda e: e.start)
    return results


def get_event_or_404(event_id: int) -> Event:
    for e in EVENTS:
        if e.id == event_id:
            return e
    abort(404)


def load_users() -> list[dict]:
    if not USERS_PATH.exists():
        USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
        USERS_PATH.write_text("[]", encoding="utf-8")
        return []
    
    try:
        content = USERS_PATH.read_text(encoding="utf-8")
        if not content.strip():  # Archivo vacío
            return []
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"⚠️ Error al leer users.json: {e}")
        print("Creando backup y reiniciando archivo...")
        
        # Crear backup del archivo corrupto
        backup_path = USERS_PATH.with_suffix('.json.bak')
        USERS_PATH.rename(backup_path)
        print(f"Backup creado en: {backup_path}")
        
        # Crear nuevo archivo vacío
        USERS_PATH.write_text("[]", encoding="utf-8")
        return []


def save_users(users: list[dict]) -> None:
    USERS_PATH.write_text(json.dumps(users, indent=2), encoding="utf-8")


def find_user_by_email(email: str) -> Optional[dict]:
    users = load_users()
    email_norm = (email or "").strip().lower()
    for u in users:
        if (u.get("email", "") or "").strip().lower() == email_norm:
            return u
    return None


def user_exists(email: str) -> bool:
    return find_user_by_email(email) is not None

def load_orders() -> list[dict]:
    if not ORDERS_PATH.exists():
        ORDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
        ORDERS_PATH.write_text("[]", encoding="utf-8")
    return json.loads(ORDERS_PATH.read_text(encoding="utf-8"))


def save_orders(orders: list[dict]) -> None:
    ORDERS_PATH.write_text(json.dumps(orders, indent=2), encoding="utf-8")


def next_order_id(orders: list[dict]) -> int:
    return max([o.get("id", 0) for o in orders], default=0) + 1

def migrate_user_passwords():
    """
    Convierte contraseñas en texto plano al nuevo formato con hash.
    Esta función debe ejecutarse una sola vez para migrar usuarios existentes.
    """
    users = load_users()
    modified = False
    
    for user in users:
        password = user.get("password")
        # Si la contraseña es un string (formato antiguo)
        if isinstance(password, str):
            print(f"Migrando usuario: {user.get('email')} - password en texto plano detectado")
            # Crear hash de la contraseña
            user["password"] = hash_password(password)
            modified = True
    
    if modified:
        save_users(users)
        print("✅ Usuarios migrados al nuevo formato de hash")
    else:
        print("✓ No se encontraron usuarios con password en texto plano")

with app.app_context():
    migrate_user_passwords()


# -----------------------------
# Rutas
# -----------------------------
@app.get("/")
def index():
    q = request.args.get("q", "")
    city = request.args.get("city", "Any")
    date_str = request.args.get("date", "")
    category = request.args.get("category", "All")

    date = _parse_date(date_str)
    events = filter_events(q=q, city=city, date=date, category=category)

    featured = events[:3] 
    upcoming = events[:6]

    return render_template(
        "index.html",
        q=q,
        city=city,
        date_str=date_str,
        category=category,
        categories=CATEGORIES,
        cities=CITIES,
        featured=featured,
        upcoming=upcoming,
    )


@app.get("/event/<int:event_id>")
def event_detail(event_id: int):
    event = next((e for e in load_events() if e.id == event_id), None)
    if not event:
        abort(404)

    similar = [e for e in EVENTS if e.category == event.category and e.id != event.id][:5]

    return render_template(
        "event_detail.html",
        event=event,
        similar=similar,
    )


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
            buy_error="Not enough tickets available for that quantity."
        ), 400

    return redirect(url_for("checkout", event_id=event.id, qty=qty))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        registered = request.args.get("registered")
        msg = "Account created successfully. Please sign in." if registered == "1" else None
        return render_template("login.html", info_message=msg)

    email = request.form.get("email", "")
    password = request.form.get("password", "")

    field_errors = {}

    if not email.strip():
        field_errors["email"] = "Email is required."
    if not password.strip():
        field_errors["password"] = "Password is required."

    if field_errors:
        return render_template(
            "login.html",
            error="Please fix the highlighted fields.",
            field_errors=field_errors,
            form={"email": email},
        ), 400

    user = find_user_by_email(email)
    if not user:
        return render_template(
            "login.html",
            error="Invalid credentials.",
            field_errors={"email": " ", "password": " "},
            form={"email": email},
        ), 401

    # Verificar la contraseña
    stored_password = user.get("password")
    
    # Si la contraseña almacenada es un string (formato antiguo), rechazar login
    if isinstance(stored_password, str):
        return render_template(
            "login.html",
            error="Invalid credentials.",
            field_errors={"email": " ", "password": " "},
            form={"email": email},
        ), 401
    
    # Verificar con el nuevo sistema de hash
    if not verify_password(password, stored_password):
        return render_template(
            "login.html",
            error="Invalid credentials.",
            field_errors={"email": " ", "password": " "},
            form={"email": email},
        ), 401

    # Establecer sesión con tiempo de login
    session["user_email"] = (user.get("email") or "").strip().lower()
    session["login_time"] = datetime.utcnow().isoformat()

    return redirect(url_for("dashboard"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    full_name = request.form.get("full_name", "")
    email = request.form.get("email", "")
    phone = request.form.get("phone", "")
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    agree = request.form.get("agree") == "on"

    # Validar términos y condiciones
    if not agree:
        return render_template(
            "register.html",
            error="You must agree to the Terms & Privacy."
        ), 400

    # Validar que las contraseñas coincidan
    if password != confirm_password:
        return render_template(
            "register.html",
            error="Passwords do not match."
        ), 400

    # Validar fortaleza de la contraseña
    password_errors = []
    if len(password) < 8:
        password_errors.append("at least 8 characters")
    if not any(c.isupper() for c in password):
        password_errors.append("at least one uppercase letter")
    if not any(c.islower() for c in password):
        password_errors.append("at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        password_errors.append("at least one number")
    if not any(c in "!@#$%^&*" for c in password):
        password_errors.append("at least one special character (!@#$%^&*)")

    if password_errors:
        return render_template(
            "register.html",
            error="Password must include: " + ", ".join(password_errors)
        ), 400

    if user_exists(email):
        return render_template(
            "register.html",
            error="This email is already registered. Try signing in."
        ), 400

    users = load_users()
    next_id = (max([u.get("id", 0) for u in users], default=0) + 1)

    # Generar hash de la contraseña
    password_hash = hash_password(password)
    
    # Cifrar el número de teléfono antes de almacenarlo
    encrypted_phone = encrypt_sensitive_data(phone) if phone else None

    users.append({
        "id": next_id,
        "full_name": full_name,
        "email": email,
        "phone": encrypted_phone,  # Guardar teléfono cifrado
        "password": password_hash,  # Guardar el diccionario con el hash
        "role": "user",          
        "status": "active",
    })

    save_users(users)

    return redirect(url_for("login", registered="1"))

@app.route("/logout")
def logout():
    """
    Cierra la sesión del usuario actual:
    - Elimina toda la información de la sesión
    - Redirige a la página principal
    """
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('index'))

@app.get("/dashboard")
@login_required
def dashboard():
    paid = request.args.get("paid") == "1"
    user = get_current_user()
    
    # Descifrar el teléfono para mostrarlo en el dashboard si es necesario
    user_phone = None
    if user and user.get("phone"):
        user_phone = decrypt_sensitive_data(user.get("phone"))
    
    return render_template(
        "dashboard.html", 
        user_name=(user.get("full_name") if user else "User"), 
        user_phone=user_phone,
        paid=paid
    )

@app.route("/checkout/<int:event_id>", methods=["GET", "POST"])
def checkout(event_id: int):
    events = load_events()
    event = next((e for e in events if e.id == event_id), None)
    if not event:
        abort(404)

    qty = _safe_int(request.args.get("qty", "1"), default=1, min_v=1, max_v=8)

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
            form_data={}
        )

    card_number = request.form.get("card_number", "")
    exp_date = request.form.get("exp_date", "")
    cvv = request.form.get("cvv", "")
    name_on_card = request.form.get("name_on_card", "")
    billing_email = request.form.get("billing_email", "")

    clean, errors = validate_payment_form(
        card_number=card_number,
        exp_date=exp_date,
        cvv=cvv,
        name_on_card=name_on_card,
        billing_email=billing_email
    )

    form_data = {
        "exp_date": clean.get("exp_date", ""),
        "name_on_card": clean.get("name_on_card", ""),
        "billing_email": clean.get("billing_email", ""),
        "card": clean.get("card", "")
    }

    if errors:
        return render_template(
            "checkout.html",
            event=event, qty=qty, subtotal=subtotal,
            service_fee=service_fee, total=total,
            errors=errors, form_data=form_data
        ), 400

    orders = load_orders()
    order_id = next_order_id(orders)
    
    # Cifrar el email de facturación antes de almacenarlo
    encrypted_billing_email = encrypt_sensitive_data(clean.get("billing_email", ""))

    # Ofuscar el número de tarjeta
    card_number_full = clean.get("card", "")
    last_four = card_number_full[-4:] if len(card_number_full) >= 4 else ""
    obfuscated_card = f"**** **** **** {last_four}" if last_four else ""

    orders.append({
        "id": order_id,
        "user_email": "PLACEHOLDER@EMAIL.COM",
        "event_id": event.id,
        "event_title": event.title,
        "qty": qty,
        "unit_price": event.price_usd,
        "service_fee": service_fee,
        "total": total,
        "status": "PAID",
        "created_at": datetime.utcnow().isoformat(),
        "payment": {
            "card": obfuscated_card,
            "exp_date": form_data.get("exp_date", ""),
            "name_on_card": form_data.get("name_on_card", ""),
            "billing_email": encrypted_billing_email
        }
    })

    save_orders(orders)

    return redirect(url_for("dashboard", paid="1"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_current_user()
    if not user:
        session.clear()
        return redirect(url_for("login"))

    # Descifrar el teléfono para mostrarlo en el formulario
    user_phone = ""
    if user.get("phone"):
        decrypted_phone = decrypt_sensitive_data(user.get("phone"))
        user_phone = decrypted_phone if decrypted_phone else ""

    form = {
        "full_name": user.get("full_name", ""),
        "email": user.get("email", ""),
        "phone": user_phone,
    }

    field_errors = {}  
    success_msg = None

    if request.method == "POST":
        full_name = request.form.get("full_name", "")
        phone = request.form.get("phone", "")

        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_new_password = request.form.get("confirm_new_password", "")

        users = load_users()
        email_norm = (user.get("email") or "").strip().lower()

        for u in users:
            if (u.get("email") or "").strip().lower() == email_norm:
                u["full_name"] = full_name
                
                # Cifrar el nuevo número de teléfono si se proporcionó
                if phone:
                    u["phone"] = encrypt_sensitive_data(phone)
                else:
                    u["phone"] = None

                # Si se está cambiando la contraseña
                if new_password:
                    # Verificar que la contraseña actual sea correcta
                    stored_password = u.get("password")
                    if isinstance(stored_password, str):
                        field_errors["current_password"] = "Invalid current password"
                        break
                    
                    if not verify_password(current_password, stored_password):
                        field_errors["current_password"] = "Current password is incorrect"
                        break
                    
                    # Verificar que las nuevas contraseñas coincidan
                    if new_password != confirm_new_password:
                        field_errors["new_password"] = "New passwords do not match"
                        break
                    
                    # Actualizar con nuevo hash
                    u["password"] = hash_password(new_password)
                
                break

        if not field_errors:
            save_users(users)
            form["full_name"] = full_name
            form["phone"] = phone
            success_msg = "Profile updated successfully."
        else:
            # Recargar el usuario actualizado para el formulario
            user = find_user_by_email(email_norm)
            user_phone = ""
            if user.get("phone"):
                decrypted_phone = decrypt_sensitive_data(user.get("phone"))
                user_phone = decrypted_phone if decrypted_phone else ""
            
            form = {
                "full_name": user.get("full_name", ""),
                "email": user.get("email", ""),
                "phone": user_phone,
            }

    return render_template(
        "profile.html",
        form=form,
        field_errors=field_errors,
        success_message=success_msg,
    )

@app.get("/admin/users")
@login_required
def admin_users():
    q = (request.args.get("q") or "").strip().lower()
    role = (request.args.get("role") or "all").strip().lower()
    status = (request.args.get("status") or "all").strip().lower()
    lockout = (request.args.get("lockout") or "all").strip().lower()

    users = [_user_with_defaults(u) for u in load_users()]
    
    # Descifrar teléfonos para mostrarlos en la vista de admin
    for user in users:
        if user.get("phone"):
            decrypted = decrypt_sensitive_data(user.get("phone"))
            user["phone_display"] = decrypted if decrypted else "[Cifrado]"
        else:
            user["phone_display"] = ""

    # filtros
    if q:
        users = [
            u for u in users
            if q in (u.get("full_name","").lower()) or q in (u.get("email","").lower())
        ]

    if role != "all":
        users = [u for u in users if (u.get("role","user").lower() == role)]

    if status != "all":
        users = [u for u in users if (u.get("status","active").lower() == status)]

    if lockout != "all":
        if lockout == "locked":
            users = [u for u in users if (u.get("locked_until") or "").strip()]
        elif lockout == "not_locked":
            users = [u for u in users if not (u.get("locked_until") or "").strip()]

    users.sort(key=lambda u: (u.get("full_name","").lower(), u.get("id", 0)))

    return render_template(
        "admin_users.html",
        users=users,
        filters={"q": q, "role": role, "status": status, "lockout": lockout},
        total=len(users),
    )

@app.post("/admin/users/<int:user_id>/toggle")
@login_required
def admin_toggle_user(user_id: int):
    users = load_users()
    for u in users:
        if int(u.get("id", 0)) == user_id:
            u.setdefault("status", "active")
            u["status"] = "disabled" if u["status"] == "active" else "active"
            break
    save_users(users)
    return redirect(url_for("admin_users"))

@app.post("/admin/users/<int:user_id>/role")
@login_required
def admin_change_role(user_id: int):
    new_role = request.form.get("role", "user")

    users = load_users()
    for u in users:
        if int(u.get("id", 0)) == user_id:
            u["role"] = new_role
            break
    save_users(users)
    return redirect(url_for("admin_users"))

if __name__ == "__main__":
    app.run(debug=True)