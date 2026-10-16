import type { ReactNode } from "react";
import { Button } from "./Primitives";

/* ============================================================================
 * 6. SKELETON LOADER (Zero-Layout-Shift Connection Resilience)
 * ========================================================================== */

export interface SkeletonProps {
  className?: string;
  label?: string;
}

export function Skeleton({
  className = "h-5 w-full",
  label = "Loading content",
}: SkeletonProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label={label}
      className={[
        "animate-eden-skeleton rounded-[var(--radius-sm)]",
        className,
      ].join(" ")}
    />
  );
}

export function CourseCardSkeleton() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading programme card"
      className="min-h-[340px] rounded-[var(--radius-md)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] p-5 shadow-[var(--shadow-card)] flex flex-col justify-between"
    >
      <div>
        <div className="flex gap-2 mb-4">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-6 w-48" />
        </div>
        <Skeleton className="h-8 w-4/5 mb-3" />
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-11/12 mb-5" />
        <div className="border-t border-dashed border-[var(--color-border-hairline)] pt-3 space-y-2">
          <Skeleton className="h-3.5 w-3/4" />
          <Skeleton className="h-3.5 w-2/3" />
        </div>
      </div>
      <div className="mt-5 flex items-center justify-between border-t border-[var(--color-border-hairline)] pt-4">
        <div className="space-y-1.5">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="h-7 w-36" />
        </div>
        <Skeleton className="h-10 w-36" />
      </div>
    </div>
  );
}

/* ============================================================================
 * 7. EMPTY STATE COMPONENT
 * ========================================================================== */

export interface EmptyStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: ReactNode;
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <section
      aria-live="polite"
      className="rounded-[var(--radius-md)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] px-6 py-12 text-center shadow-[var(--shadow-card)]"
    >
      <p className="font-clinical-mono text-xs uppercase tracking-widest text-[var(--color-accent-terracotta)]">
        No Matching Records
      </p>
      <h2 className="mt-2 font-editorial text-2xl font-semibold text-[var(--color-text-primary)]">
        {title}
      </h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-[var(--color-text-secondary)]">
        {description}
      </p>
      {actionLabel && onAction && (
        <div className="mt-6">
          <Button variant="secondary" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      )}
    </section>
  );
}

/* ============================================================================
 * 8. ERROR STATE COMPONENT
 * ========================================================================== */

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Unable to load academic catalog data",
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <section
      role="alert"
      className="rounded-[var(--radius-md)] border border-[var(--color-badge-residency-required-border)] bg-[var(--color-status-danger-bg)] p-6 text-[var(--color-status-danger-text)]"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider">
            System Diagnostic Alert
          </p>
          <h2 className="mt-1 font-editorial text-xl font-semibold">{title}</h2>
          <p className="mt-1 text-sm opacity-90">{message}</p>
        </div>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry Connection
          </Button>
        )}
      </div>
    </section>
  );
}