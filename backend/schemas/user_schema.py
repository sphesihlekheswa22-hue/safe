"""Validation for user-related payloads (register / login / role assignment)."""
from utils.validators import ValidationError, require
from utils.security import normalize_email, is_strong_password, clean_str
from utils.rbac import Role


def validate_register(data: dict) -> dict:
    require(data, "name", "email", "password")
    name = clean_str(data.get("name"), 120)
    email = normalize_email(data.get("email"))
    password = data.get("password") or ""
    if not name:
        raise ValidationError("Name is required.", "name")
    if not email:
        raise ValidationError("A valid email address is required.", "email")
    if not is_strong_password(password):
        raise ValidationError(
            "Password must be at least 8 characters and include a letter and a number.",
            "password",
        )
    return {"name": name, "email": email, "password": password}


def validate_login(data: dict) -> dict:
    email = normalize_email(data.get("email"))
    password = data.get("password") or ""
    if not email or not password:
        raise ValidationError("Email and password are required.")
    return {"email": email, "password": password}


def validate_role_assignment(data: dict) -> dict:
    role = (data.get("role") or "").upper()
    if not Role.is_valid(role):
        raise ValidationError("Invalid role.", "role")
    return {"role": role}
