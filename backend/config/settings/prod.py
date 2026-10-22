"""
Production settings for Eden Training Institute and Therapy (EdenLMS).
Configured for Decoupled Edge Architecture:
- React Frontend + Edge Proxy on Cloudflare (`https://*.workers.dev` / `https://*.pages.dev`)
- Django API + Instructor Admin on Render (`https://edenlms-api.onrender.com`)
- Serverless PostgreSQL on Neon (`DATABASE_URL`)
"""
from .base import *  # noqa: F403

DEBUG = False
ALLOW_DEV_SANDBOX = False

# Keep Instructor Admin login frictionless (Email + Password + django-axes lockout) for Dr. Violet
ENFORCE_STAFF_2FA = False

# Allow requests proxied from Cloudflare Workers (.workers.dev), Cloudflare Pages (.pages.dev), and Render
ALLOWED_HOSTS = list(
    {
        *env.list(  # noqa: F405
            "DJANGO_ALLOWED_HOSTS",
            default=[
                ".onrender.com",
                ".workers.dev",
                ".pages.dev",
                "localhost",
                "127.0.0.1",
            ],
        ),
        ".onrender.com",
        ".workers.dev",
        ".pages.dev",
        "localhost",
        "127.0.0.1",
    }
)

DATABASES = {
    "default": env.db(  # noqa: F405
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",  # noqa: F405
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)  # noqa: F405

# Trust TLS termination headers from Cloudflare / Render reverse proxies
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

# Authorize Render, Cloudflare Pages, and Cloudflare Workers origins (RUF005 compliant)
CSRF_TRUSTED_ORIGINS = list(
    {
        *env.list(  # noqa: F405
            "CSRF_TRUSTED_ORIGINS",
            default=[
                "https://*.onrender.com",
                "https://*.pages.dev",
                "https://*.workers.dev",
            ],
        ),
        "https://*.onrender.com",
        "https://*.pages.dev",
        "https://*.workers.dev",
    }
)

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.pages\.dev$",
    r"^https://.*\.workers\.dev$",
    r"^https://.*\.onrender\.com$",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
