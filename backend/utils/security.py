"""Security helpers: password hashing and input validation."""
import re

from email_validator import validate_email, EmailNotValidError

from extensions import bcrypt

# At least 8 chars, one letter and one number. Kept deliberately simple but
# meaningful so registration rejects obviously weak passwords.
_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash for ``plain``."""
    return bcrypt.generate_password_hash(plain).decode("utf-8")


def verify_password(password_hash: str, plain: str) -> bool:
    """Constant-time check of ``plain`` against a stored bcrypt hash."""
    if not password_hash or not plain:
        return False
    return bcrypt.check_password_hash(password_hash, plain)


def is_strong_password(password: str) -> bool:
    return bool(password) and bool(_PASSWORD_RE.match(password))


def normalize_email(email: str):
    """Validate and normalize an email address.

    Returns the normalized email string, or ``None`` if invalid.
    """
    if not email:
        return None
    try:
        # check_deliverability=False keeps it offline/fast for local dev.
        result = validate_email(email.strip(), check_deliverability=False)
        return result.normalized.lower()
    except EmailNotValidError:
        return None


def clean_str(value, max_len: int = 500):
    """Trim and length-limit a free-text string input. Returns None if empty."""
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    return value[:max_len]
