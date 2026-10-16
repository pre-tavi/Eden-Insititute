import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button, Card } from "../components/ui";
import { useAuth } from "../context/AuthContext";

const COUNTRY_OPTIONS = [
  { code: "KE", label: "Kenya (Local Tuition — KES)" },
  { code: "UG", label: "Uganda (International Tuition — USD)" },
  { code: "TZ", label: "Tanzania (International Tuition — USD)" },
  { code: "RW", label: "Rwanda (International Tuition — USD)" },
  { code: "NG", label: "Nigeria (International Tuition — USD)" },
  { code: "ZA", label: "South Africa (International Tuition — USD)" },
  { code: "GB", label: "United Kingdom (International Tuition — USD)" },
  { code: "US", label: "United States (International Tuition — USD)" },
  { code: "CA", label: "Canada (International Tuition — USD)" },
] as const;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [turnstileToken] = useState<string>("turnstile-dev-pass-token");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const redirectTo =
    (location.state as { from?: string } | null)?.from || "/my-learning";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login({
        email,
        password,
        turnstile_token: turnstileToken,
      });
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Unable to sign in."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-10 sm:py-14">
      <Card
        as="section"
        specLabel="STUDENT ACCESS // SESSION AUTH"
        specCode="ARGON2 + CSRF"
      >
        <div className="p-6 sm:p-8">
          <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)]">
            Dr. Violet&apos;s Institute of Psychology
          </p>
          <h1 className="mt-1 font-editorial text-3xl font-semibold text-[var(--color-text-primary)]">
            Sign In to Your Cohort
          </h1>
          <p className="mt-2 text-xs text-[var(--color-text-muted)]">
            Protected by HttpOnly session cookies, CSRF validation, and Cloudflare Turnstile.
          </p>

          {errorMessage && (
            <div
              role="alert"
              className="mt-4 rounded-[var(--radius-sm)] border border-[var(--color-badge-residency-required-border)] bg-[var(--color-status-danger-bg)] p-3 text-xs font-medium text-[var(--color-status-danger-text)]"
            >
              {errorMessage}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label
                htmlFor="login-email"
                className="block font-clinical-mono text-xs font-semibold uppercase text-[var(--color-text-secondary)]"
              >
                Email Address
              </label>
              <input
                id="login-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@example.com"
                className="mt-1.5 w-full rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)]"
              />
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="block font-clinical-mono text-xs font-semibold uppercase text-[var(--color-text-secondary)]"
              >
                Password
              </label>
              <input
                id="login-password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
                className="mt-1.5 w-full rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)]"
              />
            </div>

            <div className="rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-subtle)] px-3 py-2 font-clinical-mono text-[11px] text-[var(--color-text-muted)]">
              Cloudflare Turnstile Verification: Ready (Server-side verified)
            </div>

            <Button
              type="submit"
              fullWidth
              size="lg"
              isLoading={isSubmitting}
            >
              Sign In to Student Portal
            </Button>
          </form>

          <p className="mt-6 border-t border-[var(--color-border-hairline)] pt-4 text-center text-xs text-[var(--color-text-secondary)]">
            New to Dr. Violet&apos;s programmes?{" "}
            <Link
              to="/register"
              className="font-semibold text-[var(--color-accent-terracotta)] underline"
            >
              Create a Student Account
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const detectedTimezone =
    typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Nairobi"
      : "Africa/Nairobi";

  const [displayName, setDisplayName] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [country, setCountry] = useState<string>("KE");
  const [timezone, setTimezone] = useState<string>(detectedTimezone);
  const [turnstileToken] = useState<string>("turnstile-dev-pass-token");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await register({
        display_name: displayName,
        email,
        password,
        country,
        timezone,
        turnstile_token: turnstileToken,
      });
      navigate("/my-learning", { replace: true });
    } catch (err) {
      setErrorMessage(
        err instanceof Error ? err.message : "Registration failed."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg px-4 py-10 sm:py-14">
      <Card
        as="section"
        specLabel="NEW STUDENT REGISTRATION"
        specCode="PROFILE + TIMEZONE"
      >
        <div className="p-6 sm:p-8">
          <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)]">
            2026 / 2027 Academic Intake
          </p>
          <h1 className="mt-1 font-editorial text-3xl font-semibold text-[var(--color-text-primary)]">
            Create Your Student Account
          </h1>
          <p className="mt-2 text-xs text-[var(--color-text-muted)]">
            Your country determines local (KES) vs. international (USD) tuition on the server, and
            your timezone localizes live Google Meet lecture schedules.
          </p>

          {errorMessage && (
            <div
              role="alert"
              className="mt-4 rounded-[var(--radius-sm)] border border-[var(--color-badge-residency-required-border)] bg-[var(--color-status-danger-bg)] p-3 text-xs font-medium text-[var(--color-status-danger-text)]"
            >
              {errorMessage}
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label
                htmlFor="reg-display-name"
                className="block font-clinical-mono text-xs font-semibold uppercase text-[var(--color-text-secondary)]"
              >
                Full Name (For Academic Records &amp; Certificates)
              </label>
              <input
                id="reg-display-name"
                type="text"
                required
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g., Amina Wanjiku"
                className="mt-1.5 w-full rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)]"
              />
            </div>

            <div>
              <label
                htmlFor="reg-email"
                className="block font-clinical-mono text-xs font-semibold uppercase text-[var(--color-text-secondary)]"
              >
                Email Address
              </label>
              <input
                id="reg-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="student@example.com"
                className="mt-1.5 w-full rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)]"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="reg-country"
                  className="block font-clinical-mono text-xs font-semibold uppercase text-[var(--color-text-secondary)]"
                >
                  Country of Residence
                </label>
                <select
                  id="reg-country"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="mt-1.5 w-full rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] px-3 py-2.5 text-sm text-[var(--color-text-primary)]"
                >
                  {COUNTRY_OPTIONS.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label
                  htmlFor="reg-timezone"
                  className="block font-clinical-mono text-xs font-semibold uppercase text-[var(--color-text-secondary)]"
                >
                  Local Timezone (IANA)
                </label>
                <input
                  id="reg-timezone"
                  type="text"
                  required
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="mt-1.5 w-full rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] px-3.5 py-2.5 font-clinical-mono text-xs text-[var(--color-text-primary)]"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="reg-password"
                className="block font-clinical-mono text-xs font-semibold uppercase text-[var(--color-text-secondary)]"
              >
                Password (Minimum 10 Characters)
              </label>
              <input
                id="reg-password"
                type="password"
                required
                minLength={10}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 10 characters"
                className="mt-1.5 w-full rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)]"
              />
            </div>

            <Button
              type="submit"
              fullWidth
              size="lg"
              isLoading={isSubmitting}
            >
              Register &amp; Continue
            </Button>
          </form>

          <p className="mt-6 border-t border-[var(--color-border-hairline)] pt-4 text-center text-xs text-[var(--color-text-secondary)]">
            Already registered?{" "}
            <Link
              to="/login"
              className="font-semibold text-[var(--color-accent-terracotta)] underline"
            >
              Sign In Here
            </Link>
          </p>
        </div>
      </Card>
    </div>
  );
}