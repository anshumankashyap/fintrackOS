"""
utils/helpers.py
─────────────────
General-purpose helper functions used across the project.

Functions:
  - generate_secret_key()       — for scripts / management commands
  - mask_email(email)           — for safe logging (alice@example.com → a***@example.com)
  - truncate_string(s, max_len) — safe string truncation with ellipsis
  - parse_bool(value)           — convert env-var strings to booleans
"""

import secrets
import string


def generate_secret_key(length: int = 50) -> str:
    """
    Generate a cryptographically secure random Django SECRET_KEY.

    Usage:
        python -c "from utils.helpers import generate_secret_key; print(generate_secret_key())"
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def mask_email(email: str) -> str:
    """
    Partially mask an email address for safe logging.

    Examples:
        alice@example.com   → a***@example.com
        bob.smith@test.org  → b***@test.org
    """
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


def truncate_string(s: str, max_len: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to max_len characters, appending suffix if truncated.

    Example:
        truncate_string("Hello World", 8) → "Hello..."
    """
    if not s or len(s) <= max_len:
        return s
    return s[: max_len - len(suffix)] + suffix


def parse_bool(value) -> bool:
    """
    Convert environment-variable style strings to Python booleans.

    Truthy:  "true", "1", "yes", "on"
    Falsy:   "false", "0", "no", "off", "", None

    Example:
        parse_bool("True")  → True
        parse_bool("0")     → False
    """
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}