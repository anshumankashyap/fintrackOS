"""
finance_backend/settings/development.py
────────────────────────────────────────
Development settings — local machine only.
Enables debug toolbar, relaxed security, SQLite fallback.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# ── Dev Database: SQLite for zero-config local testing ────────────
# Comment out to use PostgreSQL locally instead
import os
if not os.environ.get("USE_POSTGRES"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }

# ── Disable caching in development ───────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

# ── Email: print to console in dev ───────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── Relaxed CORS for dev ─────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ── Relax throttling in dev ───────────────────────────────────────
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}
