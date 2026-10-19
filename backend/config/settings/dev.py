"""
Development & Test settings for Eden Training Institute and Therapy (EdenLMS).
- Connects the running application (`manage.py migrate`, `seed_catalog`, `runserver`) directly
  to Neon PostgreSQL when `DATABASE_URL` is present in `.env.local` or `.env`.
- Uses fast local SQLite during `pytest` runs (unless `PYTEST_USE_NEON=1` is set) so test
  teardown does not collide with Neon's PgBouncer connection pooler.
"""
import os
import sys

from .base import *  # noqa: F403

DEBUG = env.bool("DJANGO_DEBUG", default=True)  # noqa: F405

running_pytest = "pytest" in sys.modules and not os.environ.get("PYTEST_USE_NEON")

if running_pytest:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }
else:
    DATABASES = {
        "default": env.db(  # noqa: F405
            "DATABASE_URL",
            default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",  # noqa: F405
        )
    }
