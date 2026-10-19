import { Link, useLocation, useNavigate } from "react-router-dom";
import type { AuthUser } from "../../types/auth";
import type { AudienceTier } from "../../types/catalog";

export interface NavbarProps {
  audience: AudienceTier;
  onAudienceChange: (audience: AudienceTier) => void;
  user?: AuthUser | null;
  onLogout?: () => Promise<void>;
}

export function Navbar({
  audience,
  onAudienceChange,
  user,
  onLogout,
}: NavbarProps) {
  const location = useLocation();
  const navigate = useNavigate();

  const detectedTimezone =
    user?.profile?.timezone ||
    (typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Nairobi"
      : "Africa/Nairobi");

  const isActive = (path: string) =>
    path === "/"
      ? location.pathname === "/" || location.pathname.startsWith("/courses")
      : location.pathname.startsWith(path);

  const handleLogoutClick = async () => {
    if (onLogout) {
      await onLogout();
      navigate("/");
    }
  };

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)]">
      {/* Top Clinical & TVETA Registry Strip */}
      <div className="bg-[var(--color-bg-inverse)] px-4 py-1.5 text-[var(--color-text-inverse)]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 font-clinical-mono text-[11px]">
          <span>
            EDEN TRAINING INSTITUTE &amp; THERAPY · LIC: TVETA/PRIVATE/TVC/0019/2016 · BURUBURU PHASE II, NAIROBI
          </span>
          <span className="text-amber-300">
            TEL: +254 722 466 014 · TIMEZONE: {detectedTimezone}
          </span>
        </div>
      </div>

      {/* Main Navigation Row */}
      <nav
        aria-label="Primary Navigation"
        className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3.5"
      >
        <Link to="/" className="group flex flex-col">
          <span className="font-editorial text-xl sm:text-2xl font-semibold tracking-tight text-[var(--color-text-primary)]">
            Eden Training Institute &amp; Therapy
          </span>
          <span className="font-clinical-mono text-[11px] uppercase tracking-widest text-[var(--color-text-muted)]">
            Dr. Violet&apos;s Clinical LMS · KNEC &amp; TVETA Accredited
          </span>
        </Link>

        <div className="flex flex-wrap items-center gap-3 sm:gap-6">
          <div className="flex items-center gap-4 text-sm font-semibold">
            <Link
              to="/"
              aria-current={isActive("/") ? "page" : undefined}
              className={
                isActive("/")
                  ? "text-[var(--color-accent-terracotta)] underline underline-offset-4"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              }
            >
              Programmes
            </Link>
            <Link
              to="/my-learning"
              aria-current={isActive("/my-learning") ? "page" : undefined}
              className={
                isActive("/my-learning")
                  ? "text-[var(--color-accent-terracotta)] underline underline-offset-4"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
              }
            >
              My Learning
            </Link>

            {user ? (
              <div className="flex items-center gap-3">
                <span className="hidden sm:inline font-clinical-mono text-xs text-[var(--color-text-muted)]">
                  {user.profile?.display_name || user.email}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    void handleLogoutClick();
                  }}
                  className="text-xs font-clinical-mono uppercase tracking-wider text-[var(--color-accent-terracotta)] hover:underline"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Link
                  to="/login"
                  aria-current={isActive("/login") ? "page" : undefined}
                  className={
                    isActive("/login")
                      ? "text-[var(--color-accent-terracotta)] underline underline-offset-4"
                      : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                  }
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="rounded-[var(--radius-sm)] bg-[var(--color-brand-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--color-text-inverse)] hover:bg-[var(--color-brand-primary-hover)]"
                >
                  Register
                </Link>
              </div>
            )}
          </div>

          <div
            role="group"
            aria-label="Select Tuition Currency Display"
            className="inline-flex rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-subtle)] p-0.5"
          >
            <button
              type="button"
              aria-pressed={audience === "local"}
              onClick={() => onAudienceChange("local")}
              className={[
                "px-2.5 py-1 font-clinical-mono text-xs font-semibold rounded-[2px] transition-colors",
                audience === "local"
                  ? "bg-[var(--color-brand-primary)] text-[var(--color-text-inverse)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
              ].join(" ")}
            >
              Local (KES)
            </button>
            <button
              type="button"
              aria-pressed={audience === "international"}
              onClick={() => onAudienceChange("international")}
              className={[
                "px-2.5 py-1 font-clinical-mono text-xs font-semibold rounded-[2px] transition-colors",
                audience === "international"
                  ? "bg-[var(--color-brand-primary)] text-[var(--color-text-inverse)]"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]",
              ].join(" ")}
            >
              Intl (USD)
            </button>
          </div>
        </div>
      </nav>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-auto border-t border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)]">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3 text-sm text-[var(--color-text-secondary)]">
          <div>
            <p className="font-editorial text-lg font-semibold text-[var(--color-text-primary)]">
              Eden Training Institute and Therapy
            </p>
            <p className="mt-1 font-clinical-mono text-[11px] font-semibold text-[var(--color-accent-terracotta)]">
              TVETA Reg: TVETA/PRIVATE/TVC/0019/2016 (Licensed 28/01/2016)
            </p>
            <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">
              Accredited Technical &amp; Vocational College offering KNEC-examined Diploma in
              Counseling (Marriage &amp; Family Therapy Option) and Certificate programmes.
            </p>
          </div>

          <div>
            <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-text-primary)]">
              Campus Location &amp; 5-Day Practical Residency
            </p>
            <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">
              <strong>Nairobi Campus:</strong> Shepherds Building, Buruburu Phase II, Mumias South
              Road, Nairobi County (plus <strong>Embu</strong> practical residency block). The{" "}
              <strong>$100 USD</strong> residency fee covers daily lunch and teas; travel and
              lodging are the student&apos;s responsibility.
            </p>
          </div>

          <div>
            <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-text-primary)]">
              Official Registry Contacts &amp; Admissions
            </p>
            <ul className="mt-1.5 space-y-1 font-clinical-mono text-xs text-[var(--color-text-muted)]">
              <li>Postal: P.O. Box 70139 – 00400, Nairobi, Kenya</li>
              <li>
                Phone:{" "}
                <a
                  href="tel:+254722466014"
                  className="text-[var(--color-text-primary)] underline"
                >
                  +254 722 466 014 (0722 466 014)
                </a>
              </li>
              <li>
                Email:{" "}
                <a
                  href="mailto:edentherapycentre@gmail.com"
                  className="text-[var(--color-text-primary)] underline"
                >
                  edentherapycentre@gmail.com
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-6 border-t border-[var(--color-border-subtle)] pt-4 flex flex-wrap items-center justify-between gap-2 font-clinical-mono text-xs text-[var(--color-text-muted)]">
          <span>
            © {new Date().getFullYear()} Eden Training Institute and Therapy · All Rights Reserved
          </span>
          <span>
            DPO Pay Verified Tuition · Live Sessions Stored in UTC &amp; Displayed in Local Timezone
          </span>
        </div>
      </div>
    </footer>
  );
}