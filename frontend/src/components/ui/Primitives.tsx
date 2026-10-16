import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from "react";
import {
  formatMinorCurrency,
  getWesternCompetitorBenchmark,
  type AudienceTier,
  type CourseLevel,
  type PriceItem,
  type ResidencyMode,
} from "../../types/catalog";

/* ============================================================================
 * 1. BUTTON COMPONENT
 * ========================================================================== */

export type ButtonVariant = "primary" | "secondary" | "outline" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  isLoading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  isLoading = false,
  disabled,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  const sizeClasses: Record<ButtonSize, string> = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2.5 text-sm",
    lg: "px-5 py-3 text-base",
  };

  const variantStyles: Record<ButtonVariant, string> = {
    primary:
      "bg-[var(--color-brand-primary)] text-[var(--color-text-inverse)] border border-[var(--color-brand-primary)] hover:bg-[var(--color-brand-primary-hover)]",
    secondary:
      "bg-[var(--color-bg-subtle)] text-[var(--color-text-primary)] border border-[var(--color-border-hairline)] hover:bg-[var(--color-bg-muted)]",
    outline:
      "bg-transparent text-[var(--color-text-primary)] border border-[var(--color-border-strong)] hover:bg-[var(--color-bg-subtle)]",
    ghost:
      "bg-transparent text-[var(--color-text-secondary)] border border-transparent hover:bg-[var(--color-bg-subtle)]",
  };

  const isDisabled = disabled || isLoading;

  return (
    <button
      type={rest.type ?? "button"}
      disabled={isDisabled}
      aria-busy={isLoading || undefined}
      className={[
        "inline-flex items-center justify-center gap-2 font-semibold transition-colors rounded-[var(--radius-sm)]",
        sizeClasses[size],
        isDisabled
          ? "bg-[var(--color-bg-muted)] text-[var(--color-text-muted)] border border-[var(--color-border-hairline)] cursor-not-allowed opacity-80"
          : variantStyles[variant],
        fullWidth ? "w-full" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    >
      {isLoading ? (
        <>
          <span
            aria-hidden="true"
            className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
          <span>Processing…</span>
        </>
      ) : (
        children
      )}
    </button>
  );
}

/* ============================================================================
 * 2. CARD COMPONENT (Blended Editorial Surface + Swiss Clinical Spec Header)
 * ========================================================================== */

export interface CardProps extends HTMLAttributes<HTMLElement> {
  as?: "article" | "div" | "section" | "aside";
  specCode?: string;
  specLabel?: string;
  children: ReactNode;
}

export function Card({
  as: Component = "article",
  specCode,
  specLabel,
  className = "",
  children,
  ...rest
}: CardProps) {
  return (
    <Component
      className={[
        "bg-[var(--color-bg-surface)] border border-[var(--color-border-hairline)] rounded-[var(--radius-md)] shadow-[var(--shadow-card)] flex flex-col justify-between overflow-hidden",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...rest}
    >
      {(specLabel || specCode) && (
        <div className="flex items-center justify-between border-b border-[var(--color-border-hairline)] bg-[var(--color-bg-subtle)] px-4 py-2 font-clinical-mono text-xs font-semibold text-[var(--color-text-secondary)]">
          <span>{specLabel}</span>
          {specCode && (
            <span className="text-[var(--color-text-muted)]">{specCode}</span>
          )}
        </div>
      )}
      {children}
    </Component>
  );
}

/* ============================================================================
 * 3. BADGE COMPONENT (Level & Three-State Residency)
 * ========================================================================== */

export interface BadgeProps {
  level?: CourseLevel;
  residency?: ResidencyMode;
  children?: ReactNode;
  className?: string;
}

export function Badge({
  level,
  residency,
  children,
  className = "",
}: BadgeProps) {
  let styleVars =
    "bg-[var(--color-bg-subtle)] text-[var(--color-text-secondary)] border-[var(--color-border-hairline)]";
  let defaultLabel: ReactNode = children;

  if (level === "certificate") {
    styleVars =
      "bg-[var(--color-badge-certificate-bg)] text-[var(--color-badge-certificate-text)] border-[var(--color-badge-certificate-border)]";
    defaultLabel = children ?? "Certificate";
  } else if (level === "diploma") {
    styleVars =
      "bg-[var(--color-badge-diploma-bg)] text-[var(--color-badge-diploma-text)] border-[var(--color-badge-diploma-border)]";
    defaultLabel = children ?? "Diploma";
  } else if (residency === "optional") {
    styleVars =
      "bg-[var(--color-badge-residency-optional-bg)] text-[var(--color-badge-residency-optional-text)] border-[var(--color-badge-residency-optional-border)]";
    defaultLabel =
      children ?? "Optional 5-Day Nairobi / Embu Residency ($100 USD)";
  } else if (residency === "required") {
    styleVars =
      "bg-[var(--color-badge-residency-required-bg)] text-[var(--color-badge-residency-required-text)] border-[var(--color-badge-residency-required-border)]";
    defaultLabel =
      children ?? "Required 5-Day Nairobi / Embu Residency ($100 USD)";
  } else if (residency === "none") {
    styleVars =
      "bg-[var(--color-badge-residency-none-bg)] text-[var(--color-badge-residency-none-text)] border-[var(--color-badge-residency-none-border)]";
    defaultLabel = children ?? "100% Online (No Residency)";
  }

  return (
    <span
      className={[
        "inline-flex items-center border px-2.5 py-0.5 rounded-[var(--radius-sm)] font-clinical-mono text-xs font-semibold uppercase tracking-wider",
        styleVars,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {defaultLabel}
    </span>
  );
}

/* ============================================================================
 * 4. PRICE TAG COMPONENT (Explicit Local KES vs International USD Minor Units)
 * ========================================================================== */

export interface PriceTagProps {
  prices: PriceItem[];
  audience: AudienceTier;
  level?: CourseLevel;
  size?: "md" | "lg";
  showBenchmark?: boolean;
}

export function PriceTag({
  prices,
  audience,
  level = "certificate",
  size = "md",
  showBenchmark = true,
}: PriceTagProps) {
  const matchedPrice =
    prices.find((p) => p.audience === audience) ?? prices[0] ?? null;
  const alternatePrice = prices.find((p) => p.audience !== audience) ?? null;

  if (!matchedPrice) {
    return (
      <div className="font-clinical-mono text-sm text-[var(--color-text-muted)]">
        Tuition schedule pending
      </div>
    );
  }

  const formattedPrimary = formatMinorCurrency(
    matchedPrice.amount_minor,
    matchedPrice.currency
  );

  return (
    <div className="flex flex-col">
      <span className="font-clinical-mono text-[11px] uppercase tracking-wider text-[var(--color-text-muted)]">
        {matchedPrice.audience === "local"
          ? "Local Tuition (Kenya)"
          : "International Tuition"}
      </span>
      <div className="flex items-baseline gap-2">
        <span
          className={[
            "font-clinical-mono font-semibold text-[var(--color-text-primary)]",
            size === "lg" ? "text-2xl sm:text-3xl" : "text-xl",
          ].join(" ")}
        >
          {formattedPrimary}
        </span>
        {alternatePrice && (
          <span className="font-clinical-mono text-xs text-[var(--color-text-muted)]">
            ({formatMinorCurrency(alternatePrice.amount_minor, alternatePrice.currency)})
          </span>
        )}
      </div>
      {showBenchmark && (
        <span className="mt-0.5 text-xs text-[var(--color-text-muted)]">
          US/UK Equivalent: {getWesternCompetitorBenchmark(level)} · Includes LMS &amp; video fee
        </span>
      )}
    </div>
  );
}

/* ============================================================================
 * 5. PROGRESS BAR COMPONENT (Lesson & Cohort Completion Tracking)
 * ========================================================================== */

export interface ProgressBarProps {
  value: number;
  label?: string;
  showPercentage?: boolean;
}

export function ProgressBar({
  value,
  label = "Course completion progress",
  showPercentage = true,
}: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));

  return (
    <div className="w-full">
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="font-medium text-[var(--color-text-secondary)]">
          {label}
        </span>
        {showPercentage && (
          <span className="font-clinical-mono font-semibold text-[var(--color-text-primary)]">
            {clamped}%
          </span>
        )}
      </div>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2.5 w-full overflow-hidden rounded-full bg-[var(--color-bg-muted)] border border-[var(--color-border-hairline)]"
      >
        <div
          className="h-full bg-[var(--color-brand-primary)] transition-all duration-300"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}