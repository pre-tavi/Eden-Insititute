# Dr. Violet's LMS — Blueprint

Drop this in your repo as `docs/BLUEPRINT.md`. Companion file: `docs/PREDEPLOY_SECURITY.md`.

Workflow: one git branch per phase (`p1-design`, `p2-auth`, ...), one PR to yourself, tag when the gate passes (`v0.1-p1`). Every phase has a prompt you paste into Antigravity, a definition of done, and a demo gate for Dr. Violet.

---

## 1. The system in one page (the part to show Dr. Violet)

### What a student experiences

```
Discover catalog -> Register -> Verify email -> Choose course -> Pay (DPO link)
   -> Enrollment becomes ACTIVE -> Join cohort
   -> Watch lessons (secure video) + attend live lectures (Google Meet link)
   -> Progress is tracked per lesson -> (optional) book 5-day residency
   -> Complete -> Certificate
```

Student screens: Catalog, Course detail (price, outline, residency info), Register/Login, My Learning (progress bars, "continue where you left off"), Lesson player, Live sessions calendar (shown in the student's own timezone), Payments and receipts, Residency booking.

### What Dr. Violet experiences (instructor back-office)

For the first release this is the Django admin, customised. It is already secure, already built, and she can use it on day one. A custom instructor dashboard is a Phase 6 decision, not a starting point.

- Courses and cohorts: create, price (local and international), open/close enrollment
- Lessons: order modules, attach recordings, publish/unpublish
- Live sessions: schedule, paste the Meet link, later attach the recording
- Students: who is enrolled, paid or pending, progress percentage per student
- Payments: DPO status per student, plus a "mark as paid manually" action for bank/M-Pesa edge cases
- Residency blocks: Nairobi and Embu dates, capacity, registered list, CSV export for the lunch-and-tea headcount

### What happens behind the scenes

```
Student browser (React + Vite + Tailwind)
      |  same-origin /api   (session cookie + CSRF, no JWT in localStorage)
      v
HTTPS host / reverse proxy  (security headers, HSTS)
      v
Django + DRF  ----> Postgres
      |-----------> DPO Pay        (hosted checkout, server-side verification)
      |-----------> Managed video host (signed, short-lived playback tokens)
      |-----------> Email provider (verification, resets, receipts)
Google Meet: live lectures (link only revealed to paid, enrolled students)
```

Why this shape: boring and maintainable. Dr. Violet needs this to last years, so every moving part is either Django (well documented, long-term support) or a managed service someone else keeps patched.

---

## 2. Dr. Violet's note — as I read it (please verify against the original)

| Item | What I read | Confidence |
|---|---|---|
| Digital infrastructure fee | Per-user LMS licence (Moodle / Canvas / Google Workspace) + secure video hosting for class playbacks; looks like "include in" tuition | Medium (first word smudged) |
| Local fees | Certificate 35-45K, Diploma 130-180K (presumably KES) | Medium-high |
| Proposed external fees | Certificate about 550 to an unclear upper bound; Diploma 1,800 USD = 232,000 (KES) | Medium. 1,800 USD x ~129 KES/USD is about 232,000, which supports the reading |
| Western/UK competitors | $1,200-3,000 (certificate level), $5,000-12,000 (diploma level) | Medium |
| Delivery | Live lectures | High |
| Residency block | 5-day practical block, Nairobi and Embu, for "those wishing to attend"; $100 covers lunch and tea; travel and lodging are the student's responsibility | High |
| Payment | Direct pay via a DPO link | Medium |

Two things this tells the build:
1. Residency is **optional** for at least some students. Your `requires_residency` boolean cannot express that. Replace it with `residency = none | optional | required`.
2. Prices differ by audience (local vs international) and are stored per currency. Do not convert with a live exchange rate; store each price explicitly.

---

## 3. Decisions to lock with Dr. Violet (one short written agreement)

Before Phase 3 (money) at the latest. These are her calls, not code problems:

1. **Ownership.** She owns the domain, hosting account, DPO merchant account, and video account; you are admin on them. Prevents lock-in and makes handover clean.
2. **Award names.** Whether "Certificate" and "Diploma" are legally the right titles for what she issues, and who regulates them. Do not generate anything titled Diploma until she confirms.
3. **Audience rule.** How a student is classed local vs international (country at registration plus manual override). Enforced on the server, never from a price sent by the browser.
4. **Residency.** Optional or required per course; capacity per block; what happens if a block is cancelled (refund or transfer).
5. **Refunds and withdrawals.** One written policy; the Enrollment states below depend on it.
6. **Support.** Who answers student emails when login breaks.
7. **Data protection.** Check whether she must register with Kenya's Data Protection Commissioner and what the privacy policy and consent text must say. International students may bring other regimes (UK/EU GDPR) into play. I am not a lawyer; she should confirm this with one.
8. **Maintenance.** What she can expect from you after launch, and for how long.

---

## 4. Data model (Django)

Keep your existing `Course` as the sellable thing. Add around it:

```
User            custom model (AbstractUser), email is the login. Do this BEFORE more migrations.
Profile         user, country, timezone, display_name

Course          title, slug, level[certificate|diploma], residency[none|optional|required], status
Price           course, audience[local|international], currency, amount_minor   (integers, never floats)
Cohort          course, starts_on, capacity, enrollment_open
Module          course, order
Lesson          module, order, kind[video|reading|live|quiz], video_asset_id (provider ID, never a raw URL)
LiveSession     cohort, starts_at (UTC), title, meet_url (never in public API), recording_lesson (nullable)

Enrollment      user, cohort, status[pending_payment|active|completed|withdrawn|refunded]
Payment         enrollment or residency_registration, provider='dpo', provider_ref, amount_minor,
                currency, status, verified_at, raw_log (JSON), UNIQUE(provider, provider_ref)
LessonProgress  user, lesson, status, last_position_s, completed_at

ResidencyBlock  location[nairobi|embu], starts_on, ends_on (5 days), capacity, fee_minor (USD 100 = 10000)
ResidencyRegistration  enrollment, block, status, payment
Certificate     enrollment, issued_at, verification_code   (only after decision 2)
```

Rules that prevent whole classes of bugs:
- Money is `amount_minor` (integer) plus a currency code.
- Store all times in UTC, display in the student's timezone. International students plus live lectures makes this essential.
- Enrollment status changes only through one function (`activate_enrollment()`), called only from verified payment or a staff action.
- Public IDs are UUIDs, not sequential integers.

---

## 5. Build order

Your three remaining research parts map to P1, P2, and P4/P5. I have added P0 (foundations), P3 (payments, because Dr. Violet's note lists it and your plan does not yet), and P7 (hardening).

**Pilot scope** = P0 to P4 with one certificate course and 3-5 real students, live lectures on Meet, manual "mark as paid" if the DPO merchant account is not approved yet. Do not let payment approval block the pilot.

### Reusable context header (paste at the top of every Antigravity task)

```
PROJECT CONTEXT
Project: LMS for Dr. Violet's international psychology students (certificate and diploma programmes).
Stack: Django (latest LTS) + DRF + Postgres in backend/; Vite + React + Tailwind in frontend/.
Auth: Django session auth + CSRF. No JWT in localStorage.
Rules:
1. Plan first: show a numbered plan and wait for my approval before editing files.
2. Small diffs, one concern per commit, conventional commit messages.
3. Write or extend tests with every change; run them and show the output.
4. No secrets in code or in VITE_* variables; read from environment.
5. Every API endpoint declares permissions explicitly and scopes queries to request.user.
6. Money is integer minor units plus currency code. Times are UTC.
7. Do not add dependencies without telling me why.
Definition of done: tests pass, `python manage.py check --deploy` shows no new warnings, no secrets in the diff, README/docs updated.
```

---

### P0 — Foundations (do first, short)

Retrofitting these later is painful. The custom user model especially: changing it after real users exist is one of the hardest Django migrations.

```
TASK P0: Foundations before new features.
1. Switch to a custom user model (AbstractUser, email as USERNAME_FIELD). This is dev data only: reset the dev DB and regenerate migrations if needed.
2. Split settings into base/dev/prod. Read SECRET_KEY, DEBUG, ALLOWED_HOSTS, DATABASE_URL from environment (django-environ). Add .env.example and a .gitignore covering .env, db.sqlite3, node_modules, dist.
3. Add pre-commit with gitleaks and ruff. Add a Makefile with `make check` (tests, pip-audit, npm audit).
4. Replace Course.requires_residency (boolean) with residency (none/optional/required) via a data migration: True -> required, False -> none.
5. Add pytest-django with one smoke test per existing endpoint.
Plan first.
```
Done when: `make check` passes, a fresh clone runs from `.env.example` in under 10 minutes.
Gate: none (internal).

### P1 — Visual design system and catalog

"Premium" is a system, not decoration: a small set of tokens, a handful of components, then pages built only from those.

```
TASK P1: Design system and catalog UI.
Before building, propose TWO art directions as static HTML mockups (catalog page + course detail). Wait for me to choose.
Then build with Tailwind:
- Design tokens (colors, type scale, spacing, radii, shadows) as CSS variables in one file.
- Components: Button, Card, Badge (level, residency), PriceTag (shows local or international price), ProgressBar, Navbar, Footer, EmptyState, Skeleton loader, ErrorState.
- Pages: Catalog (filter by level), Course detail (outline, price, residency info, enroll CTA that is disabled until P2).
Constraints: mobile-first; WCAG AA contrast; keyboard accessible; usable on slow connections (lazy-load images, no layout shift); no stock gradient-hero template look; a deliberate type pairing; real catalog data only, no lorem ipsum.
Plan first.
```
Done when: Lighthouse accessibility 90+, tested at 360px width, every state (loading, empty, error) designed.
Gate: show Dr. Violet the catalog on her phone.

### P2 — Student access and enrollment shell

```
TASK P2: Registration, login, and enrollment shell.
- Endpoints: register, login, logout, email verification, password reset, "me". Django session auth + CSRF, cookies HttpOnly + Secure + SameSite=Lax.
- Argon2 password hashing; Django password validators on.
- Rate limit login/register/reset (django-axes or DRF throttles). Add Cloudflare Turnstile on register/login/reset, verified server-side.
- Profile with country and timezone collected at registration.
- Enrollment model with status pending_payment; "Enroll" creates a pending enrollment for the right cohort.
- React: auth context, protected routes (UX only; the server is the authority), My Learning page listing the student's enrollments.
- Tests: student A cannot read or change student B's enrollment (expect 404).
Plan first.
```
Done when: the two-user isolation test passes and unauthenticated calls to every non-public endpoint return 401/403.
Gate: Dr. Violet registers as a test student.

### P3 — Payments (DPO)

```
TASK P3: Payments via DPO Pay.
- Server creates the payment request using the price for the student's audience (never a price from the client).
- Redirect the student to DPO's hosted checkout. Never touch card data.
- On return AND on DPO's server notification, verify the transaction server-to-server before marking paid. Ignore anything the browser claims.
- Idempotent handling: the same notification twice must not double-activate. UNIQUE(provider, provider_ref).
- activate_enrollment() is the only code path that sets status=active.
- Store raw provider responses in Payment.raw_log. Add a "mark paid manually" admin action that writes an audit entry.
- Check DPO's current documentation for supported currencies and methods before coding; do not assume.
Plan first.
```
Done when: duplicate-notification test passes; a tampered amount is rejected.
Gate: one real small test payment in DPO's test mode.

### P4 — Learning experience, video, live sessions

```
TASK P4: Lessons, secure video, progress, live sessions.
- Models per blueprint: Module, Lesson, LessonProgress, LiveSession.
- Video lives on a managed video host, never in Django media. The API returns a short-lived signed playback token only to students with an ACTIVE enrollment in that course. The raw video URL/ID is never in any public response.
- Player: resume from last_position_s, mark complete at 90%, progress bar updates.
- Optional deterrent: overlay the student's email faintly on the video.
- Live sessions: show next session in the student's timezone; meet_url only returned to active students, only within the join window.
- Recordings: instructor attaches a recorded lesson to a LiveSession.
Plan first.
```
Done when: an unpaid student cannot obtain a playback token (test), and progress survives a refresh.
Gate: Dr. Violet runs one full lesson as a student.

Honest note on "secure video": signed tokens and domain restriction stop casual sharing and hotlinking. They do not stop screen recording. Treat it as deterrence, say so to Dr. Violet, and rely on terms of use.

### P5 — Residency blocks

```
TASK P5: Residency.
- ResidencyBlock (Nairobi, Embu; 5 days; capacity; fee USD 100) and ResidencyRegistration.
- Course.residency = optional: show "Book a block" after enrollment; = required: block course completion until a registration exists.
- Capacity enforced in the database with a transaction (no overbooking under concurrent requests).
- Pay the USD 100 through the P3 flow. Show clearly: fee covers lunch and tea; travel and lodging are the student's responsibility.
- Admin: registered list per block with CSV export for catering.
Plan first.
```
Done when: two simultaneous bookings for the last seat result in one success.

### P6 — Instructor back-office and reporting

Customise Django admin first (list filters, inline progress, CSV exports, 2FA for staff via django-otp). Build a custom instructor dashboard only if Dr. Violet asks for something admin cannot do. Add certificate issuing only after decision 2 in section 3.

### P7 — Hardening and pilot launch

Work through `PREDEPLOY_SECURITY.md` top to bottom, run `make predeploy`, deploy to staging, then run the pilot with 3-5 students before opening to anyone else.

---

## 6. Risk register (frank version)

1. **The catalog is the easy 20%.** Identity, money, video, and operations are the other 80%. That is why the order above front-loads foundations and defers polish.
2. **Scope creep.** Quizzes, discussion forums, certificates with QR codes: all good, none in the pilot. Write them in a `LATER.md` and keep moving.
3. **You are one person and also a student.** Time-box each phase. If the timeline slips, a hosted Moodle is a legitimate fallback that keeps Dr. Violet unblocked (her own note considered it). Building custom is the right choice only if it is maintainable by you for years.
4. **Money bugs are the costly ones.** Verification, idempotency, and a monthly reconciliation (DPO report vs Payment table) are non-negotiable.
5. **Bus factor.** A short `RUNBOOK.md`: how to deploy, restore a backup, rotate keys, add a course. Test the backup restore once before launch.
6. **Regulation and privacy.** Section 3, items 2 and 7. Cheap to settle early, expensive to discover late.
7. **International users.** Low bandwidth, mobile-first, timezones, and a payment path that works from abroad.

---

## 7. How I can help from here

Bring any of these and I will turn them around in the same format:
- Paste a diff, model, or serializer and I review it against the security checklist
- Generate migrations, DRF serializers/viewsets, and tests for a phase
- Refine any phase prompt after you see what Antigravity actually plans
- Draft the one-page agreement for Dr. Violet (section 3) and a plain-language privacy notice
- Write the design token file and component specs for the art direction you choose
- Build the `make predeploy` script and the RUNBOOK