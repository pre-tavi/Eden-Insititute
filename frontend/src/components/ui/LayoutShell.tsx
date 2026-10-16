import { Link, useLocation } from "react-router-dom";
import type { AudienceTier } from "../../types/catalog";

/* ============================================================================
 * 9. NAVBAR COMPONENT (Mobile-First with Audience Currency Toggle & Timezone)
 * ========================================================================== */

export interface NavbarProps {
  audience: AudienceTier;
  onAudienceChange: (audience: AudienceTier) => void;
}

export function Navbar({ audience, onAudienceChange }: NavbarProps) {
  const location = useLocation();
  const detectedTimezone =
    typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Nairobi"
      : "Africa/Nairobi";

  const isActive = (path: string) =>
    path === "/"
      ? location.pathname === "/" || location.pathname.startsWith("/courses")
      : location.pathname.startsWith(path);

  return (
    <header className="sticky top-0 z-30 border-b border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)]">
      {/* Top Clinical Telemetry Strip */}
      <div className="bg-[var(--color-bg-inverse)] px-4 py-1.5 text-[var(--color-text-inverse)]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 font-clinical-mono text-[11px]">
          <span>
            DR. VIOLET&apos;S INSTITUTE OF PSYCHOLOGY · LIVE LECTURES &amp; NAIROBI / EMBU RESIDENCY
          </span>
          <span className="text-amber-300">
            LOCAL TIMEZONE: {detectedTimezone}
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
            Dr. Violet&apos;s Institute of Psychology
          </span>
          <span className="font-clinical-mono text-[11px] uppercase tracking-widest text-[var(--color-text-muted)]">
            Certificate &amp; Diploma Clinical LMS
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
              Catalog
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
          </div>

          {/* Audience Fee Selector (Preview Toggle; Server enforces authority at checkout) */}
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

/* ============================================================================
 * 10. FOOTER COMPONENT
 * ========================================================================== */

export function Footer() {
  return (
    <footer className="mt-auto border-t border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)]">
      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3 text-sm text-[var(--color-text-secondary)]">
          <div>
            <p className="font-editorial text-lg font-semibold text-[var(--color-text-primary)]">
              Dr. Violet&apos;s Institute of Psychology
            </p>
            <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">
              Accredited Certificate and Diploma programmes delivered via live Google Meet lectures
              and signed class playback recordings.
            </p>
          </div>

          <div>
            <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-text-primary)]">
              5-Day Practical Residency Block
            </p>
            <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">
              Held in <strong>Nairobi</strong> and <strong>Embu</strong>. Residency fee of{" "}
              <strong>$100 USD</strong> covers daily lunch and teas. Travel and lodging are the
              student&apos;s responsibility.
            </p>
          </div>

          <div>
            <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-text-primary)]">
              Tuition &amp; Security Architecture
            </p>
            <p className="mt-1.5 text-xs text-[var(--color-text-muted)]">
              Direct payments processed via DPO Pay hosted checkout. Protected by server-side
              Django session authentication and CSRF protection.
            </p>
          </div>
        </div>

        <div className="mt-6 border-t border-[var(--color-border-subtle)] pt-4 flex flex-wrap items-center justify-between gap-2 font-clinical-mono text-xs text-[var(--color-text-muted)]">
          <span>© {new Date().getFullYear()} Dr. Violet&apos;s LMS (EdenLMS)</span>
          <span>All live session timestamps stored in UTC · Displayed in student timezone</span>
        </div>
      </div>
    </footer>
  );
}