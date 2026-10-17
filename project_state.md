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

- [ ] **Task 6.1:** `backend/apps/*/admin.py` — Custom Django Admin filters, inline student progress percentages, CSV exports, and `django-otp` 2FA enforcement for staff accounts.
- [ ] **Task 7.1:** `docs/RUNBOOK.md` & `make predeploy` — Full 29-point security verification, backup restore test, and staging deployment.

---

## 3. Antigravity IDE Agent Prompts (Greenfield Sequence)

> **HOW TO USE IN ANTIGRAVITY IDE TONIGHT:**
> Always prepend the **Reusable Context Header** below to every prompt you paste into
> Antigravity IDE. Start with **PROMPT P0-A**, approve the agent's numbered plan, let
> it execute, and verify with the terminal command before moving to **PROMPT P0-B**.

### A. Reusable Context Header (Paste at the Top of Every Antigravity Prompt)

```text
PROJECT CONTEXT
Project: LMS for Dr. Violet's international psychology students (certificate and diploma programmes).
Repository State: Greenfield monorepo (backend/ and frontend/).
Stack: Django (latest LTS) + DRF + Postgres in backend/; Vite + React (TypeScript) + Tailwind CSS in frontend/.
Auth: Django session auth + CSRF (HttpOnly, Secure, SameSite=Lax cookies). NEVER store JWTs in localStorage.
Rules:
1. Plan first: show a numbered file-by-file plan and wait for my approval before creating or editing files.
2. Small diffs, one concern per commit, conventional commit messages.
3. Zero placeholders: never write TODO, ..., or stub logic. Write complete, runnable files.
4. Write or extend pytest / Vitest tests with every change; run them and show the exact terminal output.
5. No secrets in code or in VITE_* variables; read all secrets from environment variables.
6. Every API endpoint declares permission_classes explicitly (default IsAuthenticated) and scopes queries to request.user.
7. Money is always integer minor units (amount_minor) plus ISO currency code (KES, USD). All datetimes are stored in UTC.
8. Do not add third-party dependencies without stating why.
Definition of done: all tests pass, `python manage.py check --deploy` shows no unexpected warnings, no secrets in git diff, and `project_state.md` checkboxes are updated.
```

---

### B. Phase 0 Prompts

#### PROMPT P0-A — Root Hygiene (Task 0.1)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 0.1 — Root Git Hygiene
Create these files in the repo root:

1. `.gitignore` — Python, Node, IDE, .env patterns.
2. `.env.example` — Document every required env var (SECRET_KEY, DEBUG, DATABASE_URL, ALLOWED_HOSTS, DPO_API_TOKEN, DPO_COMPANY_TOKEN) with placeholder values.
3. `.pre-commit-config.yaml` — Hooks: `ruff check --fix`, `ruff format`, `gitleaks detect`.
4. `Makefile` — Targets: `check` (runs ruff, mypy-if-present, pytest), `predeploy` (runs pip-audit, check --deploy, test).

After creation, run: `git init && git add -A && git commit -m "chore: root hygiene (task 0.1)"`.
Update `project_state.md` checkbox for Task 0.1 to `[x]`.
```

#### PROMPT P0-B — Documentation (Task 0.2)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 0.2 — Documentation
Create:

1. `docs/BLUEPRINT.md` — Copy of the full architectural blueprint covering all 7 phases with model fields, endpoint signatures, and security constraints.
2. `docs/PREDEPLOY_SECURITY.md` — The 29-point security checklist as a markdown task list.

Commit: `docs: blueprint and security checklist (task 0.2)`.
Update `project_state.md` checkbox for Task 0.2 to `[x]`.
```

#### PROMPT P0-C — Backend Bootstrap (Task 0.3)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 0.3 — Backend Bootstrap
Create `backend/requirements.txt` pinning:
  Django>=5.1,<5.2
  djangorestframework>=3.15,<4
  django-environ>=0.11
  django[argon2]
  psycopg[binary]>=3.2
  django-cors-headers>=4.4
  django-axes>=7
  django-csp>=4
  pytest>=8
  pytest-django>=4.9
  pip-audit>=2.7

Then scaffold `backend/manage.py` with `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")`.
Run: `cd backend && pip install -r requirements.txt` (show output).
Commit: `chore(backend): bootstrap requirements (task 0.3)`.
Update `project_state.md` checkbox for Task 0.3 to `[x]`.
```

#### PROMPT P0-D — Django Settings (Task 0.4)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 0.4 — Django Settings
Create `backend/config/__init__.py`, `backend/config/settings/__init__.py`, and:

1. `backend/config/settings/base.py` — Read SECRET_KEY, DATABASES, INSTALLED_APPS (accounts before admin), AUTH_USER_MODEL = "accounts.User", session cookie flags, Argon2 hasher, REST_FRAMEWORK defaults, CSRF_COOKIE_HTTPONLY, AXES config, CSP.
2. `backend/config/settings/dev.py` — DEBUG=True, ALLOWED_HOSTS=["*"], console email backend.
3. `backend/config/settings/prod.py` — DEBUG=False, SECURE_SSL_REDIRECT, HSTS, read ALLOWED_HOSTS from env.
4. `backend/config/urls.py` — Include `api/` namespace stub.

DO NOT run migrations yet (User model comes in Task 0.5).
Commit: `feat(backend): split settings (task 0.4)`.
Update `project_state.md` checkbox for Task 0.4 to `[x]`.
```

#### PROMPT P0-E — User & Profile Models (Task 0.5)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 0.5 — Custom User & Profile Models
Create `backend/apps/__init__.py`, `backend/apps/accounts/__init__.py`, `backend/apps/accounts/apps.py`, and:

1. `backend/apps/accounts/models.py`:
   - `User(AbstractUser)` with `id = UUIDField(primary_key)`, `email` as `USERNAME_FIELD`, blank `username` field.
   - `Profile` with `OneToOneField(User)`, fields: `country (ISO 3166 char 2)`, `timezone (char 64)`, `display_name`.
   - Post-save signal to auto-create Profile on User creation.

2. `backend/apps/accounts/admin.py` — Register both models.

Run: `python manage.py makemigrations accounts && python manage.py migrate`.
Show output. Commit: `feat(accounts): custom user + profile (task 0.5)`.
Update `project_state.md` checkbox for Task 0.5 to `[x]`.
```

#### PROMPT P0-F — Catalog Models (Task 0.6)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 0.6 — Catalog Models
Create `backend/apps/catalog/` app with:

1. `models.py`:
   - `Course` — `title`, `slug (unique)`, `description`, `level` (TextChoices: certificate, diploma), `residency` (TextChoices: none, optional, required), `status` (TextChoices: draft, published, archived), timestamps.
   - `Price` — FK to Course, `audience` (TextChoices: local, international), `currency` (char 3), `amount_minor` (PositiveIntegerField), unique_together (course, audience).
   - `Cohort` — FK to Course, `name`, `starts_on`, `capacity` (PositiveIntegerField), `enrollment_open` (BooleanField).

2. `admin.py` — Register with appropriate list_display and filters.

Run migrations. Commit: `feat(catalog): course, price, cohort models (task 0.6)`.
Update `project_state.md` checkbox for Task 0.6 to `[x]`.
```

#### PROMPT P0-G — Catalog API & Smoke Tests (Task 0.7)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 0.7 — Catalog API & Smoke Tests
1. `backend/apps/catalog/serializers.py` — `CourseListSerializer`, `CourseDetailSerializer` (nested prices and open cohorts).
2. `backend/apps/catalog/views.py`:
   - `GET /api/health/` — Returns `{"status": "ok"}` with `AllowAny`.
   - `GET /api/catalog/courses/` — List published courses with `AllowAny`.
   - `GET /api/catalog/courses/<slug>/` — Course detail with nested prices and cohorts, `AllowAny`.
3. `backend/apps/catalog/urls.py` & wire into `config/urls.py`.
4. `backend/tests/conftest.py` — Reusable fixtures (user, course with prices, cohort).
5. `backend/tests/test_smoke.py`:
   - `test_health_returns_ok`
   - `test_catalog_list_excludes_draft`
   - `test_catalog_detail_returns_prices`

Run: `pytest -v`. Show full output.
Commit: `feat(catalog): API + smoke tests (task 0.7)`.
Update `project_state.md` checkbox for Task 0.7 to `[x]`.
```

#### PROMPT P0-H — Frontend Init (Task 0.8)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 0.8 — Frontend Initialization
1. Initialize Vite + React + TypeScript in `frontend/` (use `npm create vite@latest`).
2. Install Tailwind CSS and configure.
3. `frontend/vite.config.ts` — Add `/api` proxy to `http://127.0.0.1:8000`.
4. `frontend/src/App.tsx` — Minimal shell that fetches `/api/health/` on mount and displays the JSON status.
5. `frontend/src/api/client.ts` — Fetch wrapper that auto-includes CSRF token from cookie and credentials.

Run: `cd frontend && npm install && npm run dev` (verify no errors).
Commit: `feat(frontend): vite + react + tailwind init (task 0.8)`.
Update `project_state.md` checkbox for Task 0.8 to `[x]`.
```

---

### C. Phase 1 Prompts

#### PROMPT P1-A — Art Direction Mockups (Task 1.1)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 1.1 — Art Direction Mockups
Create two standalone HTML files (no React, just HTML + inline CSS + inline JS) in `docs/mockups/`:

1. `art-direction-a.html` — Clean, editorial style. Serif headings, generous whitespace, muted earth tones. Shows Catalog grid and a Course Detail page in a single scrollable document.
2. `art-direction-b.html` — Bold, modern tech-edu style. Sans-serif, vibrant accent colors, card-heavy UI with micro-animations. Same pages.

Both must include: Navbar with "Dr. Violet's Academy" branding, Course cards (title, level badge, residency badge, KES/USD dual pricing), Course Detail with cohort dates and "Enroll" CTA button, Footer.
Both must be mobile-responsive and WCAG AA contrast compliant.

Commit: `docs: art direction mockups (task 1.1)`.
Update `project_state.md` checkbox for Task 1.1 to `[x]`.
DO NOT proceed to Task 1.2 until I confirm which direction to use.
```

#### PROMPT P1-B — Design Tokens (Task 1.2)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 1.2 — Design Tokens
Based on the approved art direction (I will specify which), create:

`frontend/src/styles/tokens.css` — CSS custom properties for:
- Color palette (primary, secondary, accent, neutral, semantic: success/warning/error/info)
- Typography scale (font families, sizes xs through 4xl, weights, line heights)
- Spacing scale (4px base, 0.25rem increments)
- Border radii (sm, md, lg, xl, full)
- Elevation shadows (sm, md, lg)
- Transition durations and easings

Import tokens.css in `frontend/src/main.tsx`.
Commit: `feat(frontend): design tokens (task 1.2)`.
Update `project_state.md` checkbox for Task 1.2 to `[x]`.
```

#### PROMPT P1-C — UI Components (Task 1.3)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 1.3 — UI Component Library
Create reusable components in `frontend/src/components/ui/`:

1. `Button.tsx` — Variants: primary, secondary, ghost, danger. Sizes: sm, md, lg. Loading state.
2. `Card.tsx` — Composable with Card.Header, Card.Body, Card.Footer.
3. `Badge.tsx` — Variants for `level` (certificate=blue, diploma=purple) and `residency` (none=gray, optional=amber, required=green).
4. `PriceTag.tsx` — Renders dual pricing: "KES 50,000" for local, "$500 USD" for international, with a toggle or tab.
5. `ProgressBar.tsx` — Animated fill, percentage label.
6. `Navbar.tsx` — Logo, nav links, auth-aware (login/register vs. user menu).
7. `Footer.tsx` — Copyright, links.
8. `EmptyState.tsx` — Icon, title, description, optional CTA.
9. `Skeleton.tsx` — Configurable loading placeholder.
10. `ErrorState.tsx` — Error message with retry button.
11. `index.ts` — Barrel export.

Each component must have sensible Tailwind styling matching the approved design tokens.
Commit: `feat(frontend): UI component library (task 1.3)`.
Update `project_state.md` checkbox for Task 1.3 to `[x]`.
```

#### PROMPT P1-D — Catalog & Detail Pages (Task 1.4)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 1.4 — Catalog & Course Detail Pages
1. Install `react-router-dom` (state why: client-side routing for SPA).
2. `frontend/src/router.tsx` — Routes: `/` → CatalogPage, `/courses/:slug` → CourseDetailPage.
3. `frontend/src/pages/CatalogPage.tsx`:
   - Fetch `/api/catalog/courses/` on mount.
   - Render responsive grid of Course Cards using UI components.
   - Skeleton loading state, ErrorState on failure, EmptyState if no courses.
4. `frontend/src/pages/CourseDetailPage.tsx`:
   - Fetch `/api/catalog/courses/:slug/` on mount.
   - Hero section with title, level badge, residency badge.
   - Description, pricing section (PriceTag), available cohorts with dates and capacity.
   - "Enroll Now" CTA (non-functional until Phase 2).
5. Update `App.tsx` to use RouterProvider.

Run: `npm run dev` and manually verify catalog renders with backend running.
Commit: `feat(frontend): catalog + detail pages (task 1.4)`.
Update `project_state.md` checkbox for Task 1.4 to `[x]`.
```

---

### D. Phase 2 Prompts

#### PROMPT P2-A — Auth Endpoints (Task 2.1)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 2.1 — Session Auth Endpoints
Create `backend/apps/accounts/serializers.py` and `backend/apps/accounts/views.py`:

1. `POST /api/auth/register/` — Create user, auto-create profile, log in, return user data. Server-side Cloudflare Turnstile verification.
2. `POST /api/auth/login/` — Validate credentials, `django.contrib.auth.login()`, set session cookie. django-axes rate limiting.
3. `POST /api/auth/logout/` — `django.contrib.auth.logout()`, clear session.
4. `GET /api/auth/me/` — Return current user + profile (IsAuthenticated).
5. `POST /api/auth/password-reset/` — Email-based password reset flow.

All endpoints use `@method_decorator(ensure_csrf_cookie)` or `@ensure_csrf_cookie` as needed.
Wire into `backend/apps/accounts/urls.py` → `config/urls.py`.

Tests in `backend/tests/test_auth.py`:
- `test_register_creates_user_and_profile`
- `test_login_sets_session_cookie`
- `test_logout_clears_session`
- `test_me_requires_auth`

Run: `pytest -v`. Commit: `feat(accounts): session auth endpoints (task 2.1)`.
Update `project_state.md` checkbox for Task 2.1 to `[x]`.
```

#### PROMPT P2-B — Enrollment Model (Task 2.2)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 2.2 — Enrollment Model & API
Create `backend/apps/enrollments/`:

1. `models.py`:
   - `Enrollment` — FK to User, FK to Cohort, `status` (TextChoices: pending_payment, active, completed, withdrawn, refunded), timestamps, unique_together (user, cohort).
   - Custom manager with `for_user(user)` method returning `filter(user=user)`.

2. `views.py`:
   - `GET /api/enrollments/` — List user's enrollments (IsAuthenticated, scoped to request.user).
   - `POST /api/enrollments/` — Create enrollment with `pending_payment` status.
   - `GET /api/enrollments/<id>/` — Detail, scoped to request.user (404 if not owner).

3. `serializers.py` — Nested cohort and course info.

Wire URLs. Tests in `backend/tests/test_enrollments.py`:
- `test_list_enrollments_scoped_to_user`
- `test_create_enrollment_pending_payment`
- `test_detail_404_for_other_user`

Run: `pytest -v`. Commit: `feat(enrollments): model + scoped API (task 2.2)`.
Update `project_state.md` checkbox for Task 2.2 to `[x]`.
```

#### PROMPT P2-C — Auth Context & My Learning (Task 2.3)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 2.3 — Frontend Auth Context & My Learning Page
1. `frontend/src/context/AuthContext.tsx`:
   - `AuthProvider` wrapping the app.
   - `useAuth()` hook exposing: `user`, `isLoading`, `login()`, `register()`, `logout()`.
   - On mount, call `GET /api/auth/me/` to restore session.

2. `frontend/src/components/auth/LoginForm.tsx` & `RegisterForm.tsx`:
   - Controlled forms with validation.
   - CSRF token handling via `api/client.ts`.
   - Error display for invalid credentials.

3. `frontend/src/components/auth/ProtectedRoute.tsx`:
   - Redirect to `/login` if not authenticated.

4. `frontend/src/pages/LoginPage.tsx` & `frontend/src/pages/RegisterPage.tsx`.

5. `frontend/src/pages/MyLearningPage.tsx`:
   - Protected route.
   - Fetch `/api/enrollments/` and display enrollment cards with status badges.
   - EmptyState if no enrollments.

6. Update router with new routes. Update Navbar to show auth state.

Commit: `feat(frontend): auth context + my learning (task 2.3)`.
Update `project_state.md` checkbox for Task 2.3 to `[x]`.
```

#### PROMPT P2-D — Isolation Tests (Task 2.4)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 2.4 — Two-User Isolation Tests
Create `backend/tests/test_isolation.py`:

1. Fixtures: `student_a` and `student_b` users, each with their own enrollment.
2. Tests:
   - `test_student_a_cannot_list_student_b_enrollments` — student_a's list response contains only their enrollments.
   - `test_student_a_gets_404_on_student_b_enrollment_detail` — student_a requesting student_b's enrollment ID receives 404 (not 403).
   - `test_unauthenticated_cannot_access_enrollments` — Returns 403/401.

Run: `pytest -v`. Commit: `test(isolation): two-user access isolation (task 2.4)`.
Update `project_state.md` checkbox for Task 2.4 to `[x]`.
```

---

### E. Phase 3 Prompts

#### PROMPT P3-A — Payment Model & Service (Task 3.1)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 3.1 — Payment Model & Activation Service
Create `backend/apps/payments/`:

1. `models.py`:
   - `Payment` — FK to Enrollment, `provider` (char), `provider_ref` (char), `amount_minor` (PositiveIntegerField), `currency` (char 3), `status` (TextChoices: initiated, completed, failed, refunded), `raw_log` (JSONField), timestamps.
   - Constraint: `UNIQUE(provider, provider_ref)`.

2. `services.py`:
   - `activate_enrollment(payment: Payment) -> None` — Idempotent function that:
     a. Verifies payment.amount_minor matches the expected Price.amount_minor for the enrollment's cohort's course and the student's audience tier.
     b. Transitions enrollment status from `pending_payment` to `active`.
     c. Logs the transition.
     d. Raises `PaymentAmountMismatch` if amounts don't match.
     e. Is a no-op if enrollment is already `active`.

Tests in `backend/tests/test_payment_service.py`:
- `test_activate_enrollment_success`
- `test_activate_enrollment_idempotent`
- `test_activate_enrollment_amount_mismatch`

Run: `pytest -v`. Commit: `feat(payments): model + activation service (task 3.1)`.
Update `project_state.md` checkbox for Task 3.1 to `[x]`.
```

#### PROMPT P3-B — DPO Integration & Webhook (Task 3.2)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 3.2 — DPO Pay Checkout & Webhook
1. `backend/apps/payments/dpo_client.py`:
   - `create_token(amount_minor, currency, description, redirect_url, notify_url)` — XML API call to DPO to create payment token. Reads DPO_API_TOKEN and DPO_COMPANY_TOKEN from env.
   - `verify_token(transaction_token)` — Verify payment status with DPO.

2. `backend/apps/payments/views.py`:
   - `POST /api/payments/initiate/` (IsAuthenticated) — Looks up enrollment, computes audience price server-side (never trusts client amount), creates DPO token, creates Payment record, returns redirect URL.
   - `GET /api/payments/return/` (AllowAny) — DPO redirect-back handler. Verifies token, calls `activate_enrollment()`.
   - `POST /api/payments/webhook/` (AllowAny, CSRF exempt) — DPO notification handler. Verifies token, calls `activate_enrollment()`. Idempotent.

3. `backend/apps/payments/admin.py`:
   - `PaymentAdmin` with list_display, readonly raw_log.
   - Staff action: "Mark Paid Manually" — creates Payment record and calls `activate_enrollment()`, logging the admin user.

Tests in `backend/tests/test_payments.py`:
- `test_duplicate_webhook_idempotent`
- `test_tampered_amount_rejected`

Wire URLs. Run: `pytest -v`. Commit: `feat(payments): DPO integration + webhook (task 3.2)`.
Update `project_state.md` checkbox for Task 3.2 to `[x]`.
```

#### PROMPT P3-C — Payment Tests (Task 3.3)

```text
<PASTE CONTEXT HEADER ABOVE>

TASK 3.3 — Payment Integration Tests
Extend `backend/tests/test_payments.py`:

1. `test_initiate_payment_creates_record` — Mock DPO API, verify Payment is created with correct amount_minor and currency.
2. `test_initiate_payment_uses_server_price` — Even if a malicious client sends a different amount, the server uses the Price table.
3. `test_return_handler_activates_enrollment` — Mock DPO verify, check enrollment transitions to active.
4. `test_webhook_with_wrong_provider_ref_404` — Unknown provider_ref returns appropriate response.
5. `test_manual_mark_paid_creates_audit_trail` — Admin action creates Payment and logs admin user.

Run: `pytest -v`. Commit: `test(payments): integration tests (task 3.3)`.
Update `project_state.md` checkbox for Task 3.3 to `[x]`.
```

---

### F. Phase 4–7 Prompts (Summaries)

> Phases 4–7 follow the same pattern. Full prompts will be elaborated in
> `project_state.md` when Phase 3 is complete and verified. Summary outlines below:

#### Phase 4 — Classroom

- **P4-A (Task 4.1):** Create Module, Lesson, LessonProgress, LiveSession models with all field types as specified.
- **P4-B (Task 4.2):** Signed video token endpoint, time-windowed meet_url resolver, enrollment status guards.
- **P4-C (Task 4.3):** ClassroomPage with video player, resume from last_position_s, 90% auto-complete, watermark, live schedule.

#### Phase 5 — Residency

- **P5-A (Task 5.1):** ResidencyBlock and ResidencyRegistration models with select_for_update seat locking.
- **P5-B (Task 5.2):** Concurrent booking tests verifying no double-booking of final seat.

#### Phase 6 — Admin Back-Office

- **P6-A (Task 6.1):** Enhanced Django Admin with filters, progress views, CSV exports, django-otp 2FA.

#### Phase 7 — Pre-Deploy Hardening

- **P7-A (Task 7.1):** RUNBOOK.md, `make predeploy` executing full 29-point security checklist, backup restore test.

---

## 4. Progress Notes

| Date       | Task   | Agent / Person | Notes                                       |
| ---------- | ------ | -------------- | ------------------------------------------- |
| 2026-10-15 | 0.0    | Antigravity    | Created `project_state.md` — state tracker initialized. |

---

## 5. Branching Strategy

```text
main
 └── p0-foundations
      ├── Task 0.1 … 0.8 (squash-merge to main, tag: v0.0-p0)
 └── p1-design
      ├── Task 1.1 … 1.4 (squash-merge to main, tag: v0.1-p1)
 └── p2-auth
      ├── Task 2.1 … 2.4 (squash-merge to main, tag: v0.2-p2)
 └── p3-payments
      ├── Task 3.1 … 3.3 (squash-merge to main, tag: v0.3-p3)
 └── p4-classroom
      ├── Task 4.1 … 4.3 (squash-merge to main, tag: v0.4-p4)
 └── p5-residency
      ├── Task 5.1 … 5.2 (squash-merge to main, tag: v0.5-p5)
 └── p6-admin
      ├── Task 6.1       (squash-merge to main, tag: v0.6-p6)
 └── p7-hardening
      ├── Task 7.1       (squash-merge to main, tag: v0.7-p7)
```

---

## 6. Definition of Done (Global)

Every task is considered **done** when:

1. ✅ All new and existing tests pass (`pytest -v` / `npm test`).
2. ✅ `python manage.py check --deploy` shows no unexpected warnings.
3. ✅ No secrets appear in `git diff`.
4. ✅ The corresponding checkbox in **Section 2** is marked `[x]`.
5. ✅ A row is added to the **Progress Notes** table in **Section 4**.
6. ✅ Code is committed with a conventional commit message.
