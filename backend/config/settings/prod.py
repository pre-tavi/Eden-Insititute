"""
Production settings for Eden Training Institute and Therapy (EdenLMS).
Enforces HTTPS/TLS, HSTS, Secure cookies, WhiteNoise static compression,
PostgreSQL via DATABASE_URL, and disables all dev/sandbox payment and bot tokens.
"""
from .base import *  # noqa: F403

DEBUG = False
ALLOW_DEV_SANDBOX = False

DATABASES = {
    "default": env.db(  # noqa: F405
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",  # noqa: F405
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa: F405

# Trust TLS termination headers from Cloudflare / Render / Koyeb reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# Pre-Deployment Security Checklist #13 & #16: Strict HTTPS & Cookie Flags
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}