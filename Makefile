.PHONY: help check predeploy test lint audit

help:
	@echo "EdenLMS Build & Security Gate Targets:"
	@echo "  make check      - Run ruff linter, pytest suite, pip-audit, and npm audit"
	@echo "  make predeploy  - Run full 29-point release gate (gitleaks, audits, deploy check, pytest)"

check:
	ruff check backend
	cd backend && pytest
	pip-audit
	npm --prefix frontend audit --omit=dev

predeploy:
	gitleaks detect --source . --log-opts="--all"
	pip-audit
	cd frontend && npm audit --omit=dev
	cd backend && DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check --deploy --fail-level WARNING
	cd backend && pytest -q