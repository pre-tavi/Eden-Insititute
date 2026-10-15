"""
Base settings for Dr. Violet's LMS (EdenLMS).
Shared across local development, staging, and production environments.
"""
from pathlib import Path

import environ

# Build paths inside the project:
# BASE_DIR -> /home/preciousgatavi/Desktop/edenlms/backend
# REPO_DIR -> /home/preciousgatavi/Desktop/edenlms
BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_DIR = BASE_DIR.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, ["http://localhost:5173", "http://127.0.0.1:5173"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173", "http://127.0.0.1:5173"]),
    VIDEO_TOKEN_TTL_SECONDS=(int, 3600),
)

# Load .env file from repository root if present
env_file = REPO_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "axes",
    "csp",
]

LOCAL_APPS = [
    "apps.accounts.apps.AccountsConfig",
    "apps.catalog.apps.CatalogConfig",
    "apps.enrollments.apps.EnrollmentsConfig",
    "apps.payments.apps.PaymentsConfig",
    "apps.classroom.apps.ClassroomConfig",
    "apps.residency.apps.ResidencyConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Password hashing — Argon2id first per Pre-Deployment Security Checklist #10
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Internationalization & UTC Timezone enforcement
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework — Secure server-side defaults (Session + CSRF, no JWT in localStorage)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "120/minute",
        "auth": "10/minute",
        "payment": "10/minute",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Cookie & CSRF Security (Pre-Deployment Checklist #9 & #26)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days
CSRF_COOKIE_HTTPONLY = False  # React reads csrftoken cookie to send X-CSRFToken header
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

# CORS Configuration
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")

# Security Headers (Pre-Deployment Checklist #18)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# Content Security Policy (django-csp 3.8)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "https://challenges.cloudflare.com")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FRAME_SRC = ("'self'", "https://challenges.cloudflare.com")
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)

# django-axes Login Brute-Force Protection (Pre-Deployment Checklist #11)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # Lock out for 1 hour after 5 failed attempts
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
AXES_RESET_ON_SUCCESS = True

# External Integrations (Read strictly from environment variables)
DPO_COMPANY_TOKEN = env("DPO_COMPANY_TOKEN", default="")
DPO_SERVICE_TYPE = env("DPO_SERVICE_TYPE", default="")
DPO_API_URL = env("DPO_API_URL", default="https://secure.3gdirectpay.com/API/v6/")
VIDEO_SIGNING_SECRET = env("VIDEO_SIGNING_SECRET", default="")
VIDEO_TOKEN_TTL_SECONDS = env.int("VIDEO_TOKEN_TTL_SECONDS")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")
AUTH_USER_MODEL = "accounts.User"
