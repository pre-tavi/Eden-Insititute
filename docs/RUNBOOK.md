# Dr. Violet's LMS (EdenLMS) — Operations & Maintenance Runbook

Companion files: `docs/BLUEPRINT.md` and `docs/PREDEPLOY_SECURITY.md`.

---

## 1. Pre-Deploy Security Gate (`make predeploy`)

Before every staging or production release, run:

```bash
make predeploy
Code snippet
# Dr. Violet's LMS (EdenLMS) — Operations & Maintenance Runbook

Companion files: `docs/BLUEPRINT.md` and `docs/PREDEPLOY_SECURITY.md`.

---

## 1. Pre-Deploy Security Gate (`make predeploy`)

Before every staging or production release, run:

```bash
make predeploy
This executes:

Secret scanning across git history (gitleaks).

Python & Node dependency vulnerability audits (pip-audit and npm audit --omit=dev).

Production deployment security checks (python manage.py check --deploy --fail-level WARNING).

Full automated test suite (pytest -q).

2. Environment Variables & Non-Default Admin URL (Production)
In production, set the following in the host environment (never committed to Git):

DJANGO_SETTINGS_MODULE=config.settings.prod

DJANGO_DEBUG=False

DJANGO_SECRET_KEY=<64+ random character high-entropy string>

DJANGO_ALLOWED_HOSTS=lms.drvioletpsychology.org

DJANGO_ADMIN_URL=eden-instructor-backoffice/

ENFORCE_STAFF_2FA=True

DATABASE_URL=postgres://<user>:<password>@<host>:5432/<dbname>

DPO_COMPANY_TOKEN=<live DPO merchant token>

DPO_SERVICE_TYPE=<live DPO service type>

VIDEO_SIGNING_SECRET=<64+ random character HMAC signing secret>

TURNSTILE_SECRET_KEY=<live Cloudflare Turnstile secret key>

3. Database Backup & Tested Restore Procedure
A. PostgreSQL Production Backup & Restore
Bash
# Create compressed custom-format backup
pg_dump --format=custom --no-owner --no-privileges "$DATABASE_URL" > backup_$(date -u +%Y%m%dT%H%M%SZ).dump

# Verify restore into an isolated staging/restore-test database
pg_restore --clean --if-exists --no-owner --dbname="$RESTORE_TEST_DATABASE_URL" backup_latest.dump
B. Local SQLite Backup Verification
Bash
sqlite3 backend/db.sqlite3 ".backup 'backend/db_backup_verify.sqlite3'"
4. Secret & Signing Key Rotation
Video Signing Secret (VIDEO_SIGNING_SECRET): Rotate at any time; existing playback tokens have a 1-hour TTL (VIDEO_TOKEN_TTL_SECONDS=3600) and students automatically obtain a new token on refresh.

DPO Company Token (DPO_COMPANY_TOKEN): Generate the new token in the DPO Merchant Portal, update DPO_COMPANY_TOKEN in the host environment, and restart the WSGI/ASGI workers.

Django Secret Key (DJANGO_SECRET_KEY): Rotating invalidates active session cookies and pending password-reset links; schedule during low-traffic hours.

5. Monthly DPO Pay Reconciliation Procedure
At the end of each calendar month:

Export the settled transactions CSV from the DPO Pay Merchant Portal.

In the Django Admin back-office (/eden-instructor-backoffice/payments/payment/), filter by status = verified for the month.

Reconcile provider_ref, currency, and amount_minor against the DPO settlement report and verify any manual overrides against bank/M-Pesa statements.


