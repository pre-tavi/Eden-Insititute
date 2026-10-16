import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  CourseCardSkeleton,
  EmptyState,
  ErrorState,
  ProgressBar,
} from "../components/ui";
import { useAuth } from "../context/AuthContext";
import type { EnrollmentItem } from "../types/auth";
import { formatMinorCurrency, type PaginatedResponse } from "../types/catalog";

export function MyLearningPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [enrollments, setEnrollments] = useState<EnrollmentItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchEnrollments = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await fetch("/api/enrollments/", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error(
          `Failed to load student enrollments (HTTP ${response.status})`
        );
      }

      const data = (await response.json()) as PaginatedResponse<EnrollmentItem>;
      setEnrollments(data.results ?? []);
    } catch (err) {
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Unable to load your enrollments."
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchEnrollments();
  }, [fetchEnrollments]);

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
      <header className="border-b border-[var(--color-border-hairline)] pb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-clinical-mono text-xs font-semibold uppercase tracking-widest text-[var(--color-accent-terracotta)]">
            Student Learning Dashboard
          </p>
          <h1 className="mt-1 font-editorial text-3xl sm:text-4xl font-semibold text-[var(--color-text-primary)]">
            Welcome, {user?.profile?.display_name || user?.email}
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
            Registered Country:{" "}
            <strong className="font-clinical-mono">
              {user?.profile?.country ?? "KE"}
            </strong>{" "}
            · Audience Tier:{" "}
            <strong className="font-clinical-mono uppercase">
              {user?.profile?.effective_audience ?? "local"}
            </strong>{" "}
            · Timezone:{" "}
            <strong className="font-clinical-mono">
              {user?.profile?.timezone ?? "Africa/Nairobi"}
            </strong>
          </p>
        </div>

        <Link
          to="/"
          className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)] underline"
        >
          + Browse More Programmes
        </Link>
      </header>

      <div className="mt-8">
        {isLoading && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <CourseCardSkeleton />
            <CourseCardSkeleton />
          </div>
        )}

        {!isLoading && errorMessage && (
          <ErrorState
            message={errorMessage}
            onRetry={() => {
              void fetchEnrollments();
            }}
          />
        )}

        {!isLoading && !errorMessage && enrollments.length === 0 && (
          <EmptyState
            title="You have no active or pending cohort enrollments yet"
            description="Explore Dr. Violet's Certificate and Diploma programmes in Psychology and select an open intake cohort to enroll."
            actionLabel="Explore Academic Catalog"
            onAction={() => navigate("/")}
          />
        )}

        {!isLoading && !errorMessage && enrollments.length > 0 && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {enrollments.map((enrollment) => {
              const isPending = enrollment.status === "pending_payment";
              const isActive =
                enrollment.status === "active" ||
                enrollment.status === "completed";

              return (
                <Card
                  key={enrollment.id}
                  specLabel={`COHORT // ${enrollment.cohort.name.toUpperCase()}`}
                  specCode={`STATUS: ${enrollment.status.toUpperCase()}`}
                >
                  <div className="p-5 sm:p-6 flex-1 flex flex-col justify-between space-y-5">
                    <div>
                      <div className="flex flex-wrap items-center gap-2 mb-3">
                        <Badge level={enrollment.course.level}>
                          {enrollment.course.level_display}
                        </Badge>
                        <Badge residency={enrollment.course.residency}>
                          {enrollment.course.residency_display}
                        </Badge>
                      </div>

                      <h2 className="font-editorial text-2xl font-semibold text-[var(--color-text-primary)]">
                        <Link
                          to={`/courses/${enrollment.course.slug}`}
                          className="hover:text-[var(--color-accent-terracotta)]"
                        >
                          {enrollment.course.title}
                        </Link>
                      </h2>

                      <p className="mt-2 text-xs text-[var(--color-text-secondary)]">
                        Cohort Starts:{" "}
                        <strong className="font-clinical-mono">
                          {enrollment.cohort.starts_on}
                        </strong>
                      </p>

                      <div className="mt-4">
                        <ProgressBar
                          value={
                            enrollment.status === "completed"
                              ? 100
                              : isActive
                              ? 10
                              : 0
                          }
                          label={
                            isPending
                              ? "Awaiting DPO Tuition Verification"
                              : "Lesson & Live Lecture Progress"
                          }
                        />
                      </div>
                    </div>

                    <div className="border-t border-[var(--color-border-hairline)] pt-4 flex flex-wrap items-center justify-between gap-4">
                      <div>
                        <span className="block font-clinical-mono text-[11px] uppercase text-[var(--color-text-muted)]">
                          Server-Verified Tuition
                        </span>
                        <span className="font-clinical-mono text-lg font-semibold text-[var(--color-text-primary)]">
                          {enrollment.expected_price
                            ? formatMinorCurrency(
                                enrollment.expected_price.amount_minor,
                                enrollment.expected_price.currency
                              )
                            : "Assigned by Staff"}
                        </span>
                      </div>

                      {isPending ? (
                        <Button size="sm" disabled>
                          Complete DPO Payment (Phase 3)
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          onClick={() =>
                            navigate(`/courses/${enrollment.course.slug}`)
                          }
                        >
                          Enter Classroom →
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}