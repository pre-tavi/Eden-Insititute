# Dr. Violet's LMS — Single-Source-of-Truth State & Antigravity IDE Agent Prompts

> **Canonical state file.** Every agent prompt, code review, and deployment decision
> references this document. Update checkboxes and notes here *before* moving to the
> next task.
>
> **Last updated:** 2026-10-15 — Task 0.0 (initial creation)

---

## 1. System Architecture & Non-Negotiable Guardrails

- **Stack:** Django (latest LTS) + Django REST Framework (DRF) + PostgreSQL in `backend/`; Vite + React (TypeScript) + Tailwind CSS in `frontend/`.
- **Authentication:** Django Session Auth + CSRF over same-origin `/api` with `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SECURE = True`, and `SESSION_COOKIE_SAMESITE = "Lax"` (`Argon2PasswordHasher` primary). No JWTs in `localStorage`.
- **Money & Pricing:** Stored strictly in integer minor units (`amount_minor`) with explicit ISO currency codes (`KES`, `USD`) and audience tiers (`local` vs `international`), never floating-point numbers or live client-side conversions.
- **Timezones:** All timestamps stored in UTC on the server and rendered in the student's local timezone on the client.
- **Residency Model:** `Course.residency` is an enum of `none | optional | required` supporting the 5-day Nairobi and Embu practical blocks ($100 USD = `10000` minor units covering lunch and teas; travel and lodging are the student's responsibility).
- **Access Isolation:** Every private queryset is scoped to `request.user` (`for_user(request.user)` / `get_object_or_404(..., user=request.user)`), returning `404` on cross-student access attempts.

---

## 2. Atomic Feature Slicing (AFS) Master Task Tracker

### Phase 0: Greenfield Foundations (`branch: p0-foundations`)

- [x] **Task 0.0:** `project_state.md` — Initialize Single-Source-of-Truth state tracker and Antigravity agent prompt playbook.
- [x] **Task 0.1:** `.gitignore`, `.env.example`, `.pre-commit-config.yaml`, `Makefile` — Root git hygiene, `gitleaks`, `ruff`, and `make check` / `make predeploy` targets.
- [x] **Task 0.2:** `docs/BLUEPRINT.md` & `docs/PREDEPLOY_SECURITY.md` — Commit architectural blueprint and 29-point security checklist.
- [x] **Task 0.3:** `backend/requirements.txt` & `backend/manage.py` — Pin Django LTS, DRF, `django-environ`, `django[argon2]`, `psycopg[binary]`, `django-cors-headers`, `django-axes`, `django-csp`, `pytest`, `pytest-django`, `pip-audit`.
- [x] **Task 0.4:** `backend/config/settings/{base.py,dev.py,prod.py}` — Split settings reading `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL` from environment variables.
- [x] **Task 0.5:** `backend/apps/accounts/models.py` — Custom `User` model (`AbstractUser`, `email` as `USERNAME_FIELD`, UUID primary key) and `Profile` (`country`, `timezone`, `display_name`) before running first migration.
- [x] **Task 0.6:** `backend/apps/catalog/models.py` — `Course` (`title`, `slug`, `level[certificate|diploma]`, `residency[none|optional|required]`, `status`), `Price` (`course`, `audience[local|international]`, `currency`, `amount_minor`), and `Cohort` (`course`, `starts_on`, `capacity`, `enrollment_open`).
- [x] **Task 0.7:** `backend/apps/catalog/views.py` & `backend/tests/test_smoke.py` — Healthcheck + read-only public catalog endpoint (`AllowAny`) + `pytest-django` smoke test suite.
- [x] **Task 0.8:** `frontend/package.json` & `frontend/vite.config.ts` — Initialize Vite + React + TypeScript + Tailwind CSS with `/api` proxy to `http://127.0.0.1:8000`.

### Phase 1: Visual Design System & Catalog UI (`branch: p1-design`, tag: `v0.1-p1`)

- [x] **Task 1.1:** `docs/mockups/art-direction-a.html` & `docs/mockups/art-direction-b.html` — Two static HTML art direction mockups (Catalog + Course Detail) for approval prior to React build.
- [x] **Task 1.2:** `frontend/src/styles/tokens.css` — CSS custom properties for color palette, typography scale, spacing, radii, and elevation shadows.
- [x] **Task 1.3:** `frontend/src/components/ui/*` — Reusable primitives: `Button`, `Card`, `Badge` (`level`, `residency`), `PriceTag` (local KES vs. international USD), `ProgressBar`, `Navbar`, `Footer`, `EmptyState`, `Skeleton`, `ErrorState`.
- [x] **Task 1.4:** `frontend/src/pages/CatalogPage.tsx` & `frontend/src/pages/CourseDetailPage.tsx` — Mobile-first WCAG AA pages powered by live DRF catalog data and `React Router`.

### Phase 2: Student Access & Enrollment Shell (`branch: p2-auth`, tag: `v0.2-p2`)

- [x] **Task 2.1:** `backend/apps/accounts/views.py` & `serializers.py` — Session auth endpoints (`register`, `login`, `logout`, `verify-email`, `password-reset`, `me`) with `django-axes` rate limiting and server-side Cloudflare Turnstile verification.
- [x] **Task 2.2:** `backend/apps/enrollments/models.py` & `views.py` — `Enrollment` model (`pending_payment | active | completed | withdrawn | refunded`) scoped via `Enrollment.objects.for_user(request.user)`.
- [x] **Task 2.3:** `frontend/src/context/AuthContext.tsx` & `frontend/src/pages/MyLearningPage.tsx` — Login/Register forms using `useState`, protected route wrappers, and student enrollment dashboard.
- [x] **Task 2.4:** `backend/tests/test_isolation.py` — Two-user isolation tests verifying Student A receives `404` when querying Student B's enrollment.

### Phase 3: DPO Pay Integration (`branch: p3-payments`, tag: `v0.3-p3`)

- [x] **Task 3.1:** `backend/apps/payments/models.py` & `services.py` — `Payment` model (`UNIQUE(provider, provider_ref)`, `amount_minor`, `currency`, `raw_log`) and single `activate_enrollment()` state transition function.
- [x] **Task 3.2:** `backend/apps/payments/views.py` & `admin.py` — Server-computed audience price lookup, DPO hosted checkout redirect, idempotent webhook/return verification, and audited staff "Mark Paid Manually" action.
- [x] **Task 3.3:** `backend/tests/test_payments.py` — Duplicate webhook idempotency test and tampered amount rejection test.

### Phase 4: Classroom, Secure Video & Live Lectures (`branch: p4-classroom`, tag: `v0.4-p4`)

- [x] **Task 4.1:** `backend/apps/classroom/models.py` — `Module`, `Lesson` (`video | reading | live | quiz`, `video_asset_id`), `LessonProgress` (`last_position_s`, `completed_at`), and `LiveSession` (`starts_at` UTC, protected `meet_url`, `recording_lesson`).
- [x] **Task 4.2:** `backend/apps/classroom/views.py` — Short-lived signed video playback token endpoint and time-windowed `meet_url` resolver restricted strictly to `ACTIVE` enrollments.
- [x] **Task 4.3:** `frontend/src/pages/ClassroomPage.tsx` — Video player with `last_position_s` resume, 90% auto-complete trigger, faint student email watermark overlay, and local-timezone live lecture schedule.

### Phase 5: Nairobi & Embu Residency Blocks (`branch: p5-residency`, tag: `v0.5-p5`)

- [x] **Task 5.1:** `backend/apps/residency/models.py` & `views.py` — `ResidencyBlock` (`nairobi | embu`, 5 days, `capacity`, `fee_minor=10000` USD) and `ResidencyRegistration` with `select_for_update()` transactional seat locking and CSV catering export.
- [x] **Task 5.2:** `backend/tests/test_residency_concurrency.py` — Concurrent booking test verifying the final seat cannot be double-booked.

### Phase 6 & Phase 7: Instructor Back-Office & Pre-Deploy Hardening (`branch: p6-admin`, `branch: p7-hardening`)

- [x] **Task 6.1:** `backend/apps/*/admin.py` — Custom Django Admin filters, inline student progress percentages, CSV exports, and `django-otp` 2FA enforcement for staff accounts.
- [x] **Task 7.1:** `docs/RUNBOOK.md` & `make predeploy` — Full 29-point security verification, backup restore test, and staging deployment.

## Phase 8 — Real Institutional Cutover & Zero-Cost HTTPS Launch (`branch: main`)
- [x] **Task 8.1:** `Makefile` — Pin all targets (`dev`, `check`, `predeploy`, `clean-demo`) to `.venv/bin/python`.
- [x] **Task 8.2:** `backend/apps/catalog/management/commands/seed_catalog.py` — Official **Eden Training Institute and Therapy** TVETA details (`TVETA/PRIVATE/TVC/0019/2016`, KNEC Marriage & Family Therapy Diploma with 14-trainee cap, Shepherds Building Buruburu Phase II address).
- [x] **Task 8.3:** `frontend/index.html`, `LayoutShell.tsx`, & `CatalogPage.tsx` — Official Eden Training Institute and Therapy address (`P.O. Box 70139 – 00400 Nairobi`), phone (`+254 722 466 014`), email (`edentherapycentre@gmail.com`), and TVETA license badge.
- [x] **Task 8.4:** `backend/apps/accounts/turnstile.py` & `backend/apps/payments/services.py` — Strictly disable dev/sandbox tokens in production (`config.settings.prod`).
- [x] **Task 8.5:** `Dockerfile`, `render.yaml`, & `backend/config/settings/prod.py` — Production container & cloud deployment manifests.
- [x] **Task 8.6:** `frontend/src/lib/db.ts`, `scripts/test-neon.mjs`, & `backend/config/settings/dev.py` — Wired Neon PostgreSQL (`silent-morning-90482168`) with IPv4-first DNS resolution and fixed PostgreSQL `FOR UPDATE` outer-join lock.
- [x] **Task 8.7:** `.env.example`, `render.yaml`, & `DPO-PILOT-SANDBOX` — Added pre-KYC pilot checkout support and synchronized environment templates.
- [x] **Task 8.8:** `frontend/functions/api/[[path]].ts` & `seed_catalog.py` — Decoupled Cloudflare Edge proxy and seeded initial production catalog on Render + Neon.
- [x] **Task 8.9:** `package.json`, `wrangler.jsonc`, & `cloudflare-worker.mjs` — Fixed Ruff `RUF005`, simplified admin login (`ENFORCE_STAFF_2FA = False`), and wired root build for Cloudflare Workers & Pages.
- [x] **Task 8.10:** `wrangler.jsonc` & `cloudflare-worker.mjs` — Added `run_worker_first` edge routing for `/api/*`, `/eden-instructor-backoffice/*`, `/static/*`, and `/media/*`.
- [x] **Task 8.11:** `seed_catalog.py`, `payments/views.py`, `accounts/views.py`, `base.py`, & `requirements.txt` — Remediated Dev AI audit findings (removed hardcoded fallback credentials & lockout wipe on boot, added SMTP email settings & error logging, added `DpoXmlParser` for `application/xml` webhooks, and pinned `djangorestframework==3.18.3` & `certifi>=2026.10.19`).
