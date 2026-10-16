/**
 * Domain types mirroring Django REST Framework serializers in `backend/apps/catalog/serializers.py`.
 * Money is always represented in integer minor units (`amount_minor`) + ISO currency code.
 */

export type CourseLevel = "certificate" | "diploma";

export type ResidencyMode = "none" | "optional" | "required";

export type AudienceTier = "local" | "international";

export type CurrencyCode = "KES" | "USD";

export interface PriceItem {
  id: string;
  audience: AudienceTier;
  currency: CurrencyCode;
  amount_minor: number;
  amount_major: string;
}

export interface CohortPublicItem {
  id: string;
  name: string;
  starts_on: string;
  capacity: number;
  enrollment_open: boolean;
}

export interface CourseListItem {
  id: string;
  title: string;
  slug: string;
  summary: string;
  level: CourseLevel;
  level_display: string;
  residency: ResidencyMode;
  residency_display: string;
  prices: PriceItem[];
}

export interface CourseDetailItem extends CourseListItem {
  description: string;
  cohorts: CohortPublicItem[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Formats integer minor units (e.g., 3500000 -> "KES 35,000", 55000 -> "USD 550")
 * using exact integer math without floating-point rounding bugs.
 */
export function formatMinorCurrency(
  amountMinor: number,
  currency: CurrencyCode
): string {
  const wholeUnits = Math.floor(amountMinor / 100);
  const cents = Math.abs(amountMinor % 100);
  const formattedWhole = wholeUnits.toLocaleString("en-US");

  if (cents === 0) {
    return `${currency} ${formattedWhole}`;
  }
  const paddedCents = String(cents).padStart(2, "0");
  return `${currency} ${formattedWhole}.${paddedCents}`;
}

/**
 * Returns Dr. Violet's Western US/UK competitor tuition range benchmark per programme level.
 */
export function getWesternCompetitorBenchmark(level: CourseLevel): string {
  return level === "diploma" ? "$5,000 – $12,000 USD" : "$1,200 – $3,000 USD";
}