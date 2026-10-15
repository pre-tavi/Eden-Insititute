"""
Local development settings for Dr. Violet's LMS (EdenLMS).
Uses SQLite automatically if DATABASE_URL is not running locally.
"""
from .base import *
from .base import BASE_DIR, env

DEBUG = True

# In local dev, default to SQLite unless USE_POSTGRES_IN_DEV=True is explicitly set
if env.bool("USE_POSTGRES_IN_DEV", default=False):
    DATABASES = {
        "default": env.db("DATABASE_URL"),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"