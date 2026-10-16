/**
 * Authentication, Profile, and Enrollment types + CSRF session helper utilities.
 * Uses Django session cookies + X-CSRFToken over same-origin /api (no JWTs in localStorage).
 */
import type {
  AudienceTier,
  CohortPublicItem,
  CourseLevel,
  PriceItem,
  ResidencyMode,
} from "./catalog";

export interface UserProfile {
  display_name: string;
  country: string;
  timezone: string;
  effective_audience: AudienceTier;
}

export interface AuthUser {
  id: string;
  email: string;
  email_verified: boolean;
  is_staff: boolean;
  profile: UserProfile | null;
  created_at: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  turnstile_token: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  display_name: string;
  country: string;
  timezone: string;
  turnstile_token: string;
}

export type EnrollmentStatus =
  | "pending_payment"
  | "active"
  | "completed"
  | "withdrawn"
  | "refunded";

export interface CourseEnrollmentSummary {
  id: string;
  title: string;
  slug: string;
  summary: string;
  level: CourseLevel;
  level_display: string;
  residency: ResidencyMode;
  residency_display: string;
}

export interface EnrollmentItem {
  id: string;
  status: EnrollmentStatus;
  status_display: string;
  cohort: CohortPublicItem;
  course: CourseEnrollmentSummary;
  expected_price: PriceItem | null;
  activated_at: string | null;
  completed_at: string | null;
  created_at: string;
}

/**
 * Reads a cookie value by name from document.cookie (used for csrftoken).
 */
export function getCookie(name: string): string | null {
  if (typeof document === "undefined" || !document.cookie) {
    return null;
  }
  const cookies = document.cookie.split(";");
  for (const rawCookie of cookies) {
    const cookie = rawCookie.trim();
    if (cookie.startsWith(`${name}=`)) {
      return decodeURIComponent(cookie.substring(name.length + 1));
    }
  }
  return null;
}

/**
 * Ensures a valid Django CSRF token is available in cookies and returns it.
 */
export async function ensureCsrfToken(): Promise<string> {
  const existing = getCookie("csrftoken");
  if (existing) {
    return existing;
  }
  const response = await fetch("/api/auth/csrf/", {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  if (response.ok) {
    const data = (await response.json()) as { csrfToken?: string };
    if (data.csrfToken) {
      return data.csrfToken;
    }
  }
  return getCookie("csrftoken") ?? "";
}

/**
 * Formats DRF validation error payloads into a clean human-readable message.
 */
export function extractApiErrorMessage(
  payload: unknown,
  fallback = "Request could not be completed."
): string {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }
  const record = payload as Record<string, unknown>;
  if (typeof record.detail === "string") {
    return record.detail;
  }
  for (const [field, value] of Object.entries(record)) {
    if (Array.isArray(value) && value.length > 0 && typeof value[0] === "string") {
      return field === "non_field_errors" ? value[0] : `${field}: ${value[0]}`;
    }
    if (typeof value === "string") {
      return `${field}: ${value}`;
    }
  }
  return fallback;
}