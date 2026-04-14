import re
import unicodedata
from typing import Callable, Dict, Tuple

NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,60}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\d{7,15}$")
PASSWORD_SPECIAL_RE = re.compile(r"[!@#$%^&*()\-_=+\[\]{}<>?]")


def normalize_basic(value: str) -> str:
    return unicodedata.normalize("NFKC", (value or "")).strip()


def normalize_name(value: str) -> str:
    value = normalize_basic(value)
    return re.sub(r"\s+", " ", value)


def validate_full_name(full_name: str) -> Tuple[str, str]:
    full_name = normalize_name(full_name)
    if not full_name:
        return "", "Full name is required."
    if not NAME_RE.fullmatch(full_name):
        return "", "Name must be 2-60 characters and only include letters, spaces, apostrophes, or hyphens."
    return full_name, ""


def validate_email(email: str) -> Tuple[str, str]:
    email = normalize_basic(email).lower()
    if not email:
        return "", "Email is required."
    if len(email) > 254:
        return "", "Email must be 254 characters or less."
    if email.count("@") != 1 or not EMAIL_RE.fullmatch(email):
        return "", "Please enter a valid email address."
    return email, ""


def validate_phone(phone: str) -> Tuple[str, str]:
    phone = normalize_basic(phone).replace(" ", "")
    if not phone:
        return "", "Phone number is required."
    if not PHONE_RE.fullmatch(phone):
        return "", "Phone must contain only digits and be 7-15 digits long."
    return phone, ""


def validate_password(password: str, user_email: str = "") -> Tuple[str, str]:
    password = unicodedata.normalize("NFKC", password or "")
    if not password:
        return "", "Password is required."
    if len(password) < 8 or len(password) > 64:
        return "", "Password must be 8-64 characters long."
    if any(ch.isspace() for ch in password):
        return "", "Password must not contain spaces."
    if password.lower() == (user_email or "").lower():
        return "", "Password cannot be the same as the email address."
    if not re.search(r"[A-Z]", password):
        return "", "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return "", "Password must include at least one lowercase letter."
    if not re.search(r"\d", password):
        return "", "Password must include at least one number."
    if not PASSWORD_SPECIAL_RE.search(password):
        return "", "Password must include at least one special character."
    return password, ""


def validate_register_form(
    full_name: str,
    email: str,
    phone: str,
    password: str,
    confirm_password: str,
    agree: str | None,
    email_exists_checker: Callable[[str], bool],
) -> Tuple[Dict, Dict]:
    clean: Dict[str, str] = {}
    errors: Dict[str, str] = {}

    clean["full_name"], err = validate_full_name(full_name)
    if err:
        errors["full_name"] = err

    clean["email"], err = validate_email(email)
    if err:
        errors["email"] = err
    elif email_exists_checker(clean["email"]):
        errors["email"] = "This email is already registered. Try signing in."

    clean["phone"], err = validate_phone(phone)
    if err:
        errors["phone"] = err

    clean["password"], err = validate_password(password, clean.get("email", ""))
    if err:
        errors["password"] = err

    if confirm_password != password:
        errors["confirm_password"] = "Password confirmation does not match."

    if not agree:
        errors["agree"] = "You must accept Terms & Privacy."

    clean["confirm_password"] = ""
    clean["agree"] = "checked" if agree else ""
    return clean, errors


def validate_login_form(email: str, password: str) -> Tuple[Dict, Dict]:
    clean: Dict[str, str] = {}
    errors: Dict[str, str] = {}

    clean["email"], err = validate_email(email)
    if err:
        errors["email"] = err

    password = unicodedata.normalize("NFKC", password or "")
    if not password.strip():
        errors["password"] = "Password is required."
    clean["password"] = password

    return clean, errors


def validate_profile_form(
    full_name: str,
    phone: str,
    current_password: str,
    new_password: str,
    confirm_new_password: str,
    password_verifier: Callable[[str], bool],
    user_email: str,
) -> Tuple[Dict, Dict]:
    clean: Dict[str, str] = {}
    errors: Dict[str, str] = {}

    clean["full_name"], err = validate_full_name(full_name)
    if err:
        errors["full_name"] = err

    clean["phone"], err = validate_phone(phone)
    if err:
        errors["phone"] = err

    current_password = unicodedata.normalize("NFKC", current_password or "")
    new_password = unicodedata.normalize("NFKC", new_password or "")
    confirm_new_password = unicodedata.normalize("NFKC", confirm_new_password or "")

    clean["new_password"] = ""

    wants_password_change = any([current_password, new_password, confirm_new_password])
    if wants_password_change:
        if not current_password:
            errors["current_password"] = "Current password is required to change your password."
        elif not password_verifier(current_password):
            errors["current_password"] = "Current password is incorrect."

        _, err = validate_password(new_password, user_email)
        if err:
            errors["new_password"] = err

        if confirm_new_password != new_password:
            errors["confirm_new_password"] = "New password confirmation does not match."

        if not errors.get("current_password") and not errors.get("new_password") and not errors.get("confirm_new_password"):
            clean["new_password"] = new_password

    return clean, errors
