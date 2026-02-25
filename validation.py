"""
payment_validation.py

Skeleton file for input validation exercise.
You must implement each validation function according to the
specification provided in the docstrings.

All validation functions must return:

    (clean_value, error_message)

Where:
    clean_value: normalized/validated value (or empty string if invalid)
    error_message: empty string if valid, otherwise error description
"""

import re
import unicodedata
from datetime import datetime
from typing import Tuple, Dict


# =============================
# Regular Patterns
# =============================


CARD_DIGITS_RE = re.compile(r"^\d+$")  #digits only
CVV_RE = re.compile(r"^\d{3,4}$")      #3 or 4 digits
EXP_RE = re.compile(r"^(0[1-9]|1[0-2])\/\d{2}$")   #MM/YY format
EMAIL_BASIC_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")    # basic email structure
NAME_ALLOWED_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$")   # allowed name characters



# =============================
# Utility Functions
# =============================

def normalize_basic(value: str) -> str:
    """
    Normalize input using NFKC and strip whitespace.
    """
    return unicodedata.normalize("NFKC", (value or "")).strip()


def luhn_is_valid(number: str) -> bool:
    total = 0
    reverse_digits = number[::-1]

    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n

    return total % 10 == 0



# =============================
# Field Validations
# =============================

def validate_card_number(card_number: str) -> Tuple[str, str]:
    card = normalize_basic(card_number)
    card = card.replace(" ", "").replace("-", "")

    if not CARD_DIGITS_RE.match(card):
        return "", "Card number must contain digits only"

    if not (13 <= len(card) <= 19):
        return "", "Card number must be between 13 and 19 digits"

    if not luhn_is_valid(card):
        return "", "Invalid card number (Luhn check failed)"

    return card, ""


def validate_exp_date(exp_date: str) -> Tuple[str, str]:
    exp = normalize_basic(exp_date)

    if not EXP_RE.match(exp):
        return "", "Expiration date must be in MM/YY format"

    month, year = exp.split("/")
    month = int(month)
    year = int("20" + year)

    now = datetime.utcnow()

    if year < now.year or (year == now.year and month < now.month):
        return "", "Card is expired"

    if year > now.year + 15:
        return "", "Expiration date too far in future"

    return exp, ""


def validate_cvv(cvv: str) -> Tuple[str, str]:
    value = normalize_basic(cvv)

    if not CVV_RE.match(value):
        return "", "CVV must be 3 or 4 digits"

    return "", ""



def validate_billing_email(billing_email: str) -> Tuple[str, str]:
    email = normalize_basic(billing_email).lower()

    if not email:
        return "", "Email is required"

    if len(email) > 254:
        return "", "Email too long"

    if not EMAIL_BASIC_RE.match(email):
        return "", "Invalid email format"

    return email, ""



def validate_name_on_card(name_on_card: str) -> Tuple[str, str]:
    name = normalize_basic(name_on_card)

    name = " ".join(name.split())

    if not name:
        return "", "Name is required"

    if not (2 <= len(name) <= 60):
        return "", "Name must be between 2 and 60 characters"

    if not NAME_ALLOWED_RE.match(name):
        return "", "Name contains invalid characters"

    return name, ""



# =============================
# Orchestrator Function
# =============================

def validate_payment_form(
    card_number: str,
    exp_date: str,
    cvv: str,
    name_on_card: str,
    billing_email: str
) -> Tuple[Dict, Dict]:
    """
    Orchestrates all field validations.

    Returns:
        clean (dict)  -> sanitized values safe for storage/use
        errors (dict) -> field_name -> error_message
    """

    clean = {}
    errors = {}

    card, err = validate_card_number(card_number)
    if err:
        errors["card_number"] = err
    clean["card"] = card

    exp_clean, err = validate_exp_date(exp_date)
    if err:
        errors["exp_date"] = err
    clean["exp_date"] = exp_clean

    _, err = validate_cvv(cvv)
    if err:
        errors["cvv"] = err

    name_clean, err = validate_name_on_card(name_on_card)
    if err:
        errors["name_on_card"] = err
    clean["name_on_card"] = name_clean

    email_clean, err = validate_billing_email(billing_email)
    if err:
        errors["billing_email"] = err
    clean["billing_email"] = email_clean

    return clean, errors


# =============================
# Registration Field Validations
# =============================

# Regex for full name: letters (including accented), spaces, apostrophes, hyphens
FULL_NAME_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$")
# Regex for phone: only digits
PHONE_RE = re.compile(r"^\d+$")
# Regex for email: exactly one @, local part, domain with at least one dot
EMAIL_REGISTRATION_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Special characters allowed in password
PASSWORD_SPECIAL_CHARS = "!@#$%^&*()-_=+[]{}<>?"


def validate_full_name(full_name: str) -> Tuple[str, str]:
    """
    Validates and normalizes full name for registration.
    
    Requirements:
    - Min 2, max 60 characters
    - Only letters (including accented), spaces, apostrophes, hyphens
    - Collapse multiple spaces to one
    - Trim leading/trailing spaces
    """
    # Normalize and trim
    name = normalize_basic(full_name)
    
    # Collapse multiple spaces to one
    name = " ".join(name.split())
    
    if not name:
        return "", "Full name is required"
    
    if len(name) < 2:
        return "", "Full name must be at least 2 characters"
    
    if len(name) > 60:
        return "", "Full name must not exceed 60 characters"
    
    if not FULL_NAME_RE.match(name):
        return "", "Full name can only contain letters, spaces, apostrophes, and hyphens"
    
    return name, ""


def validate_registration_email(email: str, existing_users: list = None) -> Tuple[str, str]:
    """
    Validates and normalizes email for registration.
    
    Requirements:
    - Max 254 characters
    - Valid basic format (exactly one @, local part, domain with dot)
    - Normalize to lowercase
    - Must not already exist in database
    """
    # Normalize and convert to lowercase
    email_clean = normalize_basic(email).lower()
    
    if not email_clean:
        return "", "Email is required"
    
    if len(email_clean) > 254:
        return "", "Email must not exceed 254 characters"
    
    # Check for exactly one @ symbol
    if email_clean.count("@") != 1:
        return "", "Email must contain exactly one @ symbol"
    
    # Validate basic structure
    if not EMAIL_REGISTRATION_RE.match(email_clean):
        return "", "Invalid email format"
    
    # Check if email already exists
    if existing_users:
        for user in existing_users:
            if user.get("email", "").lower() == email_clean:
                return "", "This email is already registered"
    
    return email_clean, ""


def validate_phone(phone: str) -> Tuple[str, str]:
    """
    Validates and normalizes phone number for registration.
    
    Requirements:
    - Only digits
    - Length between 7 and 15 digits
    - No internal spaces stored
    """
    # Remove all spaces
    phone_clean = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    phone_clean = normalize_basic(phone_clean)
    
    if not phone_clean:
        return "", "Phone number is required"
    
    if not PHONE_RE.match(phone_clean):
        return "", "Phone number must contain only digits"
    
    if len(phone_clean) < 7:
        return "", "Phone number must be at least 7 digits"
    
    if len(phone_clean) > 15:
        return "", "Phone number must not exceed 15 digits"
    
    return phone_clean, ""


def validate_password(password: str, email: str = "", confirm_password: str = "") -> Tuple[str, str]:
    """
    Validates password for registration.
    
    Requirements:
    - Min 8, max 64 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character from: ! @ # $ % ^ & * ( ) - _ = + [ ] { } < > ?
    - No whitespace
    - Cannot equal email
    - Must match confirmation password
    """
    if not password:
        return "", "Password is required"
    
    if len(password) < 8:
        return "", "Password must be at least 8 characters"
    
    if len(password) > 64:
        return "", "Password must not exceed 64 characters"
    
    # Check for whitespace
    if any(c.isspace() for c in password):
        return "", "Password must not contain whitespace"
    
    # Check for at least one uppercase
    if not any(c.isupper() for c in password):
        return "", "Password must contain at least one uppercase letter"
    
    # Check for at least one lowercase
    if not any(c.islower() for c in password):
        return "", "Password must contain at least one lowercase letter"
    
    # Check for at least one digit
    if not any(c.isdigit() for c in password):
        return "", "Password must contain at least one number"
    
    # Check for at least one special character
    if not any(c in PASSWORD_SPECIAL_CHARS for c in password):
        return "", f"Password must contain at least one special character ({PASSWORD_SPECIAL_CHARS})"
    
    # Check password cannot equal email
    if email and password == email:
        return "", "Password cannot be the same as your email"
    
    # Check confirmation match
    if confirm_password and password != confirm_password:
        return "", "Password confirmation does not match"
    
    return password, ""


def validate_registration_form(
    full_name: str,
    email: str,
    phone: str,
    password: str,
    confirm_password: str,
    existing_users: list = None
) -> Tuple[Dict, Dict]:
    """
    Orchestrates all registration field validations.
    
    Returns:
        clean (dict)  -> sanitized values safe for storage
        errors (dict) -> field_name -> error_message
    """
    clean = {}
    errors = {}
    
    # Validate full name
    name_clean, err = validate_full_name(full_name)
    if err:
        errors["full_name"] = err
    clean["full_name"] = name_clean
    
    # Validate email (pass existing users to check duplicates)
    email_clean, err = validate_registration_email(email, existing_users)
    if err:
        errors["email"] = err
    clean["email"] = email_clean
    
    # Validate phone
    phone_clean, err = validate_phone(phone)
    if err:
        errors["phone"] = err
    clean["phone"] = phone_clean
    
    # Validate password (pass email and confirm_password)
    password_clean, err = validate_password(password, email_clean, confirm_password)
    if err:
        errors["password"] = err
    clean["password"] = password_clean
    
    return clean, errors
