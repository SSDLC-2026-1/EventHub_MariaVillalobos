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