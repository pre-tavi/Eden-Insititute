# Pre-deployment Security Checklist — Django + DRF + React/Vite

Repo location: `docs/PREDEPLOY_SECURITY.md`. Tick boxes in git so the history is your audit trail.

Several of the 20 items come from Supabase/Firebase-style stacks (public DB key, row-level security). Your stack is Django, where the browser never talks to the database. Each item below is translated to what it means for you, with a way to verify it.

---

## The 20

- [ ] **1. Hide API keys**
  Do: all secrets (Django SECRET_KEY, DPO credentials, video signing key, email key) in environment variables only. In Vite, anything prefixed `VITE_` is public in the built bundle, so no secrets there, ever.
  Verify: `npm run build && grep -rE "(secret|token|api[_-]?key)" frontend/dist | head` returns nothing sensitive.

- [ ] **2. Purge Git secrets**
  Do: `.env` in `.gitignore` from the first commit; gitleaks as a pre-commit hook.
  Verify: `gitleaks detect --source . --log-opts="--all"`. If anything is found: rotate the key FIRST (assume it is compromised), then clean history with `git filter-repo`.

- [ ] **3. Use public DB key**
  Do: not applicable to Django. The database credentials live only on the server. The rule becomes: the React app holds zero secrets; only identifiers that are safe to expose (e.g. a video playback ID that is useless without a signed token). If you ever add a client-side Supabase/Firebase call, only the public anon key may ship.
  Verify: read `frontend/.env*`; every value would be fine on a billboard.

- [ ] **4. Enable row-level security**
  Do: Django does not use RLS by default; isolation happens in the application. Every queryset is scoped to the user through one manager method (`Enrollment.objects.for_user(request.user)`). Postgres RLS can be layered on later.
  Verify: a test where student A requests student B's enrollment, progress, payment, and registration; every one returns 404.

- [ ] **5. Encrypt sensitive data**
  Do: TLS in transit (item 19); encryption at rest from the database host; collect the minimum personal data; never store card data (DPO's hosted checkout keeps you out of that scope). Field-level encryption only for fields you decide are truly sensitive.
  Verify: list every field you store about a student and justify each one.

- [ ] **6. Enforce server-side auth**
  Do: in DRF settings, `DEFAULT_PERMISSION_CLASSES = ['rest_framework.permissions.IsAuthenticated']`; public endpoints (catalog) opt in with `AllowAny`. React route guards are UX only.
  Verify: `curl -i https://staging/api/enrollments/` without a cookie returns 401/403 for every private endpoint.

- [ ] **7. Lock record access**
  Do: never fetch by ID alone. `get_object_or_404(Enrollment, pk=pk, user=request.user)`. UUID public IDs reduce guessing but are not a substitute.
  Verify: the isolation tests from item 4 run in CI.

- [ ] **8. Block field tampering**
  Do: serializers list `fields` explicitly; `status`, `paid_at`, `price`, `is_staff`, `role` are `read_only`. Prices and audience are computed on the server.
  Verify: PATCH an enrollment with `{"status": "active"}` as a student; it is ignored or rejected.

- [ ] **9. Secure session cookies**
  Do: `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = "Lax"`, `CSRF_COOKIE_SECURE = True`, set `CSRF_TRUSTED_ORIGINS`, sensible `SESSION_COOKIE_AGE`. Serve frontend and API from the same origin. No tokens in localStorage.
  Verify: browser devtools, Application tab: cookie shows HttpOnly, Secure, SameSite.

- [ ] **10. Hash passwords**
  Do: `pip install "django[argon2]"` and put `Argon2PasswordHasher` first in `PASSWORD_HASHERS`. Keep Django's validators. Never write your own hashing.
  Verify: in the shell, a new user's `password` field starts with `argon2$`.

- [ ] **11. Rate limit login**
  Do: django-axes (lock after repeated failures) plus DRF throttle scopes on login, register, password reset, and the payment-create endpoint. Add rules at the edge (Cloudflare) if you use it.
  Verify: 10 wrong passwords in a row get locked out or throttled.

- [ ] **12. Add bot protection**
  Do: Cloudflare Turnstile on register, login, and reset, with the token verified server-side (a client-side check alone is worthless).
  Verify: a register request with a missing or fake token is rejected by the API directly.

- [ ] **13. Parameterize queries**
  Do: use the ORM. If raw SQL is ever needed, pass parameters, never f-strings.
  Verify: `grep -rnE "\.raw\(|\.extra\(|cursor\.execute\(f|execute\(.*%" backend/` returns nothing unreviewed.

- [ ] **14. Validate all input**
  Do: DRF serializers and model validators are the gate (types, lengths, choices, email normalisation). Frontend validation (e.g. Zod) is for friendliness only.
  Verify: send oversized, empty, wrong-type, and unexpected-field payloads to each write endpoint.

- [ ] **15. Escape user content**
  Do: React escapes by default; ban `dangerouslySetInnerHTML` unless the content passes DOMPurify. Any rich text Dr. Violet writes (lesson notes) is sanitised on the server too. Add a Content-Security-Policy (item 18).
  Verify: `grep -rn "dangerouslySetInnerHTML" frontend/src`; try `<img src=x onerror=alert(1)>` in every text field.

- [ ] **16. Restrict file uploads**
  Do: if students upload assignments: allowlist extensions and MIME type, enforce size limits, random filenames, private storage (not served directly), never executable. Videos go to the video host, not Django.
  Verify: upload a `.html`, a `.php`, and a renamed `.exe`; all are rejected.

- [ ] **17. Trim API responses**
  Do: each serializer returns only what that screen needs. No `meet_url`, video IDs, other students' data, staff flags, or internal notes in public or student responses. Paginate lists.
  Verify: read the raw JSON of every endpoint as a student and ask of each field: does the screen need this?

- [ ] **18. Add security headers**
  Do: Django `SecurityMiddleware`, plus django-csp (check the current settings format in its docs), `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, and `frame-ancestors` to prevent clickjacking.
  Verify: scan the staging URL with Mozilla Observatory and securityheaders.com; aim for A or better.

- [ ] **19. Force HTTPS**
  Do: `SECURE_SSL_REDIRECT = True`, `SECURE_PROXY_SSL_HEADER` set correctly for your host, `SECURE_HSTS_SECONDS` (start small, raise to a year once stable), `SECURE_HSTS_INCLUDE_SUBDOMAINS`.
  Verify: `python manage.py check --deploy` is clean; `curl -I http://yourdomain` redirects to https.

- [ ] **20. Scan dependencies**
  Do: commit lockfiles; enable Dependabot or Renovate; run `pip-audit` and `npm audit --omit=dev` in `make check`.
  Verify: both commands exit 0, or each finding has a written reason in the PR.

---

## Gaps in the 20 that matter specifically for an LMS with payments

- [ ] **21. Production settings and staff accounts.** `DEBUG = False`, strict `ALLOWED_HOSTS`, admin on a non-default URL, 2FA (django-otp) for every staff account. Dr. Violet's account is the most valuable one in the system.
- [ ] **22. Payment integrity.** Verify DPO transactions server-to-server, check amount and currency against your own Price record, idempotency on notifications, monthly reconciliation of DPO report vs Payment table.
- [ ] **23. Video access.** Signed playback tokens, short expiry, tied to an active enrollment, restricted to your domain. Never a raw video URL in any response.
- [ ] **24. Backups and restore.** Automated database backups, and ONE tested restore before launch. Separate staging and production databases.
- [ ] **25. Logging and alerts.** Error tracking (e.g. Sentry), an audit log for payments, manual "mark paid" actions, and role changes.
- [ ] **26. CORS and origins.** No wildcard CORS; narrow `CSRF_TRUSTED_ORIGINS`.
- [ ] **27. Email flows.** Verification required before enrollment; reset links single-use and short-lived; same response whether or not the email exists (no account enumeration).
- [ ] **28. Privacy.** Privacy notice, consent at registration, data export and deletion path, a decision on data-protection registration (see Blueprint section 3).
- [ ] **29. Account hygiene.** 2FA on GitHub, hosting, DPO, video host, domain registrar, and email. Dr. Violet owns the accounts; you are an admin.

---

## Release gate

Add to the Makefile and run before every deploy:

```make
predeploy:
	gitleaks detect --source . --log-opts="--all"
	pip-audit
	cd frontend && npm audit --omit=dev
	cd backend && python manage.py check --deploy --fail-level WARNING
	cd backend && pytest -q
```

Ship only when `make predeploy` exits 0 and boxes 1-29 are ticked or have a written exception.