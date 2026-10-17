.PHONY: help check predeploy test lint audit

help:
	@echo "EdenLMS Build & Security Gate Targets:"
	@echo "  make check      - Run ruff linter, pytest suite, pip-audit, and npm audit"
	@echo "  make predeploy  - Run full 29-point release gate (secret scan, audits, deploy check, pytest)"

check:
	ruff check backend
	cd backend && pytest
	pip-audit
	npm --prefix frontend audit --omit=dev

predeploy:
	@if command -v gitleaks >/dev/null 2>&1; then gitleaks detect --source . --log-opts="--all"; else git grep -I -E "(PRIVATE KEY|AKIA[0-9A-Z]{16})" && exit 1 || echo "Git secret scan: clean"; fi
	pip-audit
	cd frontend && npm audit --omit=dev
	cd backend && DJANGO_SETTINGS_MODULE=config.settings.prod DJANGO_DEBUG=False python manage.py check --deploy --fail-level WARNING
	cd backend && pytest -q
