"""
finance_backend/settings/development.py
────────────────────────────────────────
Development settings — local machine only.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Dev-friendly static files (no manifest hashing)
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Silence WhiteNoise "No directory at staticfiles" when running tests / runserver before collectstatic
STATIC_ROOT.mkdir(parents=True, exist_ok=True)  # noqa: F405

# Dev Database: SQLite for zero-config local testing
import os

if not os.environ.get("USE_POSTGRES"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }

# Disable caching in development
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CORS_ALLOW_ALL_ORIGINS = True

# Keep throttle rate definitions so ScopedRateThrottle (auth scope) on Register/Login works.
# Disable global default throttles to avoid noisy rate limits in dev.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],  # noqa: F405
        "anon": "10000/minute",
        "user": "10000/minute",
        "auth": "10000/minute",
    },
}
