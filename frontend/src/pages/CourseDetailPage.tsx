import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  PriceTag,
  Skeleton,
} from "../components/ui";
import type { AudienceTier, CourseDetailItem } from "../types/catalog";

export interface CourseDetailPageProps {
  audience: AudienceTier;
}

export function CourseDetailPage({ audience }: CourseDetailPageProps) {
  const { slug } = useParams<{ slug: string }>();
  const [course, setCourse] = useState<CourseDetailItem | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [notFound, setNotFound] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchCourseDetail = useCallback(async () => {
    if (!slug) {
      setNotFound(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setNotFound(false);
    setErrorMessage(null);

    try {
      const response = await fetch(
        `/api/catalog/courses/${encodeURIComponent(slug)}/`,
        {
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        }
      );

      if (response.status === 404) {
        setNotFound(true);
        setCourse(null);
        return;
      }

      if (!response.ok) {
        throw new Error(
          `Course detail endpoint returned HTTP ${response.status}`
        );
      }

      const data = (await response.json()) as CourseDetailItem;
      setCourse(data);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Unable to load programme details.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void fetchCourseDetail();
  }, [fetchCourseDetail]);

  const detectedTimezone =
    typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Nairobi"
      : "Africa/Nairobi";

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-10 space-y-6">
        <Skeleton className="h-5 w-48" label="Loading breadcrumb" />
        <Skeleton className="h-12 w-3/4" label="Loading course title" />
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="lg:col-span-8 space-y-4">
            <Skeleton className="h-64 w-full" label="Loading syllabus" />
            <Skeleton className="h-40 w-full" label="Loading residency details" />
          </div>
          <div className="lg:col-span-4">
            <Skeleton className="h-80 w-full" label="Loading tuition panel" />
          </div>
        </div>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-10">
        <ErrorState
          message={errorMessage}
          onRetry={() => {
            void fetchCourseDetail();
          }}
        />
      </div>
    );
  }

  if (notFound || !course) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-10">
        <EmptyState
          title="Programme Not Found"
          description="The requested psychology course does not exist or has not been published yet."
        />
        <div className="mt-6 text-center">
          <Link
            to="/"
            className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)] underline"
          >
            ← Return to Academic Catalog
          </Link>
        </div>
      </div>
    );
  }

  const modules = course.description
    ? course.description
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
    : [];

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
      <div className="mb-6">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)] hover:underline"
        >
          ← Back to Programme Catalog
        </Link>
      </div>

      {/* Programme Header */}
      <header className="border-b border-[var(--color-border-hairline)] pb-6">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <Badge level={course.level}>{course.level_display}</Badge>
          <Badge residency={course.residency}>{course.residency_display}</Badge>
        </div>
        <h1 className="font-editorial text-3xl sm:text-4xl font-semibold text-[var(--color-text-primary)]">
          {course.title}
        </h1>
        <p className="mt-3 max-w-3xl text-base text-[var(--color-text-secondary)]">
          {course.summary}
        </p>
      </header>

      {/* Main Content + Tuition Panel Grid */}
      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-start">
        {/* Left Column: Syllabus + Live Lectures + Residency Block */}
        <div className="lg:col-span-8 space-y-6">
          <Card
            as="section"
            specLabel="CURRICULUM SPECIFICATION"
            specCode={`SYLLABUS // ${course.level.toUpperCase()}`}
          >
            <div className="p-5 sm:p-6">
              <h2 className="font-editorial text-2xl font-semibold text-[var(--color-text-primary)]">
                Course Outline &amp; Weekly Structure
              </h2>
              <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                Delivered via live Google Meet lectures (displayed in {detectedTimezone}) +
                short-lived signed video playbacks.
              </p>

              {modules.length > 0 ? (
                <ol className="mt-5 divide-y divide-[var(--color-border-hairline)]">
                  {modules.map((modLine, index) => (
                    <li key={index} className="py-3.5 first:pt-0 last:pb-0">
                      <span className="block font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)]">
                        UNIT 0{index + 1} · LIVE LECTURE + SIGNED PLAYBACK
                      </span>
                      <span className="mt-1 block text-sm font-medium text-[var(--color-text-primary)]">
                        {modLine}
                      </span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="mt-4 text-sm text-[var(--color-text-secondary)]">
                  Detailed syllabus units are published to enrolled cohort members.
                </p>
              )}
            </div>
          </Card>

          {/* 5-Day Practical Residency Callout (Nairobi & Embu) */}
          <section
            aria-labelledby="residency-heading"
            className="rounded-[var(--radius-md)] border border-[var(--color-accent-terracotta-border)] bg-[var(--color-accent-terracotta-bg)] p-5 sm:p-6"
          >
            <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)]">
              5-Day Practical Residency Block · Nairobi &amp; Embu
            </p>
            <h2
              id="residency-heading"
              className="mt-1 font-editorial text-xl font-semibold text-[var(--color-text-primary)]"
            >
              {course.residency === "required"
                ? "Mandatory 5-Day Practical Block Required for Completion"
                : course.residency === "optional"
                ? "Optional 5-Day In-Person Practical Block for Those Wishing to Attend"
                : "100% Online Delivery — No Physical Residency Required"}
            </h2>
            <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
              {course.residency === "none" ? (
                "This programme is completed 100% online via synchronous Google Meet seminars and protected video playbacks."
              ) : (
                <>
                  Students attending the 5-day practical block in{" "}
                  <strong>Nairobi</strong> or <strong>Embu</strong> pay a{" "}
                  <strong>$100 USD</strong> residency fee to cover daily{" "}
                  <strong>lunch and teas</strong>. Travel and lodging are the
                  student&apos;s responsibility.
                </>
              )}
            </p>
          </section>
        </div>

        {/* Right Column: Tuition, Cohorts & Phase 1 Disabled Enroll CTA */}
        <Card
          as="aside"
          specLabel="TUITION & ENROLLMENT"
          specCode="DPO PAY CHECKOUT"
          className="lg:col-span-4"
        >
          <div className="p-5 sm:p-6 space-y-5">
            <PriceTag
              prices={course.prices}
              audience={audience}
              level={course.level}
              size="lg"
            />

            <div className="rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-subtle)] p-3.5 text-xs space-y-2">
              <p className="font-clinical-mono font-semibold uppercase text-[var(--color-text-primary)]">
                Open Intake Cohorts
              </p>
              {course.cohorts.length > 0 ? (
                <ul className="space-y-1.5 text-[var(--color-text-secondary)]">
                  {course.cohorts.map((cohort) => (
                    <li
                      key={cohort.id}
                      className="flex items-center justify-between gap-2"
                    >
                      <span className="font-medium">{cohort.name}</span>
                      <span className="font-clinical-mono text-[11px]">
                        Starts {cohort.starts_on} ({cohort.capacity} seats)
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-[var(--color-text-muted)]">
                  Next intake dates announcing shortly.
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Button fullWidth size="lg" disabled>
                Enroll via DPO Pay (Unlocks in Phase 2)
              </Button>
              <p className="text-center font-clinical-mono text-[11px] text-[var(--color-text-muted)]">
                Student registration &amp; session auth activate in Phase 2.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}