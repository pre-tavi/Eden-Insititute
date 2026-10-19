.PHONY: help dev check predeploy clean-demo test lint audit

VENV_DIR := $(CURDIR)/.venv
PYTHON := $(VENV_DIR)/bin/python
PYTEST := $(VENV_DIR)/bin/pytest
RUFF := $(VENV_DIR)/bin/ruff
PIP_AUDIT := $(VENV_DIR)/bin/pip-audit

help:
	@echo "Eden Training Institute and Therapy (EdenLMS) — Build & Launch Targets:"
	@echo "  make dev         - Run Django API (127.0.0.1:8000) + React Vite UI (localhost:5173) using .venv"
	@echo "  make check       - Run ruff linter, 25-test pytest suite, pip-audit, and npm audit"
	@echo "  make predeploy   - Run full 29-point release gate (secret scan, audits, deploy check, pytest)"
	@echo "  make clean-demo  - Purge local test enrollments/payments and re-seed real TVETA catalog"

dev:
	@echo "Starting EdenLMS Backend (http://127.0.0.1:8000) and Vite Frontend (http://localhost:5173)..."
	@trap 'kill 0' INT; \
	(cd backend && $(PYTHON) manage.py runserver 127.0.0.1:8000) & \
	(npm --prefix frontend run dev) & \
	wait

check:
	$(RUFF) check backend
	cd backend && $(PYTEST)
	$(PIP_AUDIT)
	npm --prefix frontend audit --omit=dev

predeploy:
	@if command -v gitleaks >/dev/null 2>&1; then gitleaks detect --source . --log-opts="--all"; else git grep -I -E "BEGIN [A-Z ]*PRIVATE KEY" -- ":(exclude)Makefile" && exit 1 || echo "Git secret scan: clean"; fi
	$(PIP_AUDIT)
	cd frontend && npm audit --omit=dev
	cd backend && DJANGO_SETTINGS_MODULE=config.settings.prod DJANGO_DEBUG=False $(PYTHON) manage.py check --deploy --fail-level WARNING
	cd backend && $(PYTEST) -q

clean-demo:
	cd backend && $(PYTHON) manage.py shell -c "from apps.residency.models import ResidencyRegistration; from apps.payments.models import Payment; from apps.enrollments.models import Enrollment; ResidencyRegistration.objects.all().delete(); Payment.objects.all().delete(); Enrollment.objects.all().delete(); print('Cleared demo enrollments, payments, and residency bookings.')"
	cd backend && $(PYTHON) manage.py seed_catalog