import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Badge,
  Card,
  CourseCardSkeleton,
  EmptyState,
  ErrorState,
  PriceTag,
} from "../components/ui";
import type {
  AudienceTier,
  CourseLevel,
  CourseListItem,
  PaginatedResponse,
} from "../types/catalog";

export interface CatalogPageProps {
  audience: AudienceTier;
}

type LevelFilter = "all" | CourseLevel;

export function CatalogPage({ audience }: CatalogPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const rawLevel = searchParams.get("level");
  const activeLevel: LevelFilter =
    rawLevel === "certificate" || rawLevel === "diploma" ? rawLevel : "all";

  const [courses, setCourses] = useState<CourseListItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchCourses = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const query =
        activeLevel === "all"
          ? ""
          : `?level=${encodeURIComponent(activeLevel)}`;
      const response = await fetch(`/api/catalog/courses/${query}`, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });

      if (!response.ok) {
        throw new Error(
          `Catalog API responded with HTTP ${response.status} (${response.statusText})`
        );
      }

      const data = (await response.json()) as PaginatedResponse<CourseListItem>;
      setCourses(data.results ?? []);
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : "Network error while contacting the academic catalog server.";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, [activeLevel]);

  useEffect(() => {
    void fetchCourses();
  }, [fetchCourses]);

  const handleFilterChange = (nextLevel: LevelFilter) => {
    if (nextLevel === "all") {
      setSearchParams({});
    } else {
      setSearchParams({ level: nextLevel });
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
      {/* Editorial + Clinical Benchmark Header */}
      <section
        aria-labelledby="catalog-hero-heading"
        className="border-b border-[var(--color-border-hairline)] pb-8"
      >
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-end">
          <div className="lg:col-span-8">
            <p className="font-clinical-mono text-xs font-semibold uppercase tracking-widest text-[var(--color-accent-terracotta)]">
              Academic Registry · 2026 / 2027 Cohorts
            </p>
            <h1
              id="catalog-hero-heading"
              className="mt-2 font-editorial text-3xl sm:text-4xl lg:text-5xl font-semibold text-[var(--color-text-primary)]"
            >
              Clinical &amp; Counselling Psychology Programmes with Live Faculty Supervision.
            </h1>
            <p className="mt-3 max-w-2xl text-base text-[var(--color-text-secondary)]">
              Every course pairs weekly live Google Meet lectures (rendered automatically in your
              local timezone) with token-signed class playback recordings and optional or required
              5-day practical residency blocks in Nairobi and Embu.
            </p>
          </div>

          <aside
            aria-label="Global Tuition Benchmark"
            className="lg:col-span-4 rounded-[var(--radius-md)] border border-[var(--color-border-hairline)] border-l-4 border-l-[var(--color-brand-primary)] bg-[var(--color-bg-subtle)] p-4"
          >
            <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-text-primary)]">
              Tuition Transparency &amp; Value
            </p>
            <dl className="mt-2 space-y-1.5 text-xs text-[var(--color-text-secondary)]">
              <div className="flex justify-between gap-2">
                <dt className="font-semibold">Certificate Tier:</dt>
                <dd className="font-clinical-mono">
                  35–45K KES / $550–$750 (vs $1.2K–$3K US/UK)
                </dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="font-semibold">Diploma Tier:</dt>
                <dd className="font-clinical-mono">
                  130–180K KES / $1,800 (vs $5K–$12K US/UK)
                </dd>
              </div>
            </dl>
            <p className="mt-2.5 border-t border-[var(--color-border-hairline)] pt-2 font-clinical-mono text-[11px] text-[var(--color-text-muted)]">
              Digital infrastructure fee (LMS licence + secure video hosting) included in tuition.
            </p>
          </aside>
        </div>
      </section>

      {/* Level Filter Toolbar */}
      <section
        aria-label="Programme Level Filter"
        className="flex flex-wrap items-center justify-between gap-4 py-6"
      >
        <div
          role="group"
          aria-label="Filter courses by academic level"
          className="flex flex-wrap items-center gap-2"
        >
          {(
            [
              { id: "all", label: "All Programmes" },
              { id: "certificate", label: "Certificate Level" },
              { id: "diploma", label: "Diploma Level" },
            ] as const
          ).map((tab) => {
            const isSelected = activeLevel === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                aria-pressed={isSelected}
                onClick={() => handleFilterChange(tab.id)}
                className={[
                  "px-3.5 py-2 rounded-[var(--radius-sm)] font-clinical-mono text-xs font-semibold uppercase tracking-wider border transition-colors",
                  isSelected
                    ? "bg-[var(--color-brand-primary)] text-[var(--color-text-inverse)] border-[var(--color-brand-primary)]"
                    : "bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] border-[var(--color-border-hairline)] hover:bg-[var(--color-bg-subtle)]",
                ].join(" ")}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        <p className="font-clinical-mono text-xs text-[var(--color-text-muted)]">
          5-Day Practical Block (Nairobi / Embu): $100 USD covers lunch &amp; teas
        </p>
      </section>

      {/* State 1: Loading Skeleton Grid */}
      {isLoading && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <CourseCardSkeleton />
          <CourseCardSkeleton />
        </div>
      )}

      {/* State 2: Network / API Error */}
      {!isLoading && errorMessage && (
        <ErrorState
          message={errorMessage}
          onRetry={() => {
            void fetchCourses();
          }}
        />
      )}

      {/* State 3: Empty Results */}
      {!isLoading && !errorMessage && courses.length === 0 && (
        <EmptyState
          title="No published psychology programmes match this filter"
          description="Try clearing the level filter or run the seed_catalog management command to populate Dr. Violet's initial cohorts."
          actionLabel={activeLevel !== "all" ? "Show All Programmes" : undefined}
          onAction={
            activeLevel !== "all"
              ? () => handleFilterChange("all")
              : undefined
          }
        />
      )}

      {/* State 4: Live Course Cards */}
      {!isLoading && !errorMessage && courses.length > 0 && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {courses.map((course, idx) => (
            <Card
              key={course.id}
              specLabel={`LEVEL // ${course.level.toUpperCase()}`}
              specCode={`PSY-${course.level === "diploma" ? "20" : "10"}${idx + 1}`}
            >
              <div className="p-5 sm:p-6 flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2 mb-3">
                    <Badge level={course.level}>{course.level_display}</Badge>
                    <Badge residency={course.residency}>
                      {course.residency_display}
                    </Badge>
                  </div>

                  <h2 className="font-editorial text-2xl font-semibold text-[var(--color-text-primary)]">
                    <Link
                      to={`/courses/${course.slug}`}
                      className="hover:text-[var(--color-accent-terracotta)] transition-colors"
                    >
                      {course.title}
                    </Link>
                  </h2>

                  <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                    {course.summary}
                  </p>

                  {/* Swiss Specification Table inside Card */}
                  <dl className="mt-4 border-t border-dashed border-[var(--color-border-hairline)] pt-3 space-y-1.5 text-xs text-[var(--color-text-secondary)]">
                    <div className="flex justify-between gap-2">
                      <dt className="font-clinical-mono text-[var(--color-text-muted)]">
                        DELIVERY:
                      </dt>
                      <dd className="font-medium text-right">
                        Live Google Meet Lectures + Signed Video Playbacks
                      </dd>
                    </div>
                    <div className="flex justify-between gap-2">
                      <dt className="font-clinical-mono text-[var(--color-text-muted)]">
                        RESIDENCY:
                      </dt>
                      <dd className="font-medium text-right">
                        {course.residency === "none"
                          ? "100% Online (No physical block required)"
                          : course.residency === "optional"
                          ? "Optional 5-Day Nairobi/Embu ($100 USD lunch & tea)"
                          : "Required 5-Day Nairobi/Embu ($100 USD lunch & tea)"}
                      </dd>
                    </div>
                  </dl>
                </div>

                <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-[var(--color-border-hairline)] pt-4">
                  <PriceTag
                    prices={course.prices}
                    audience={audience}
                    level={course.level}
                  />
                  <Link
                    to={`/courses/${course.slug}`}
                    className="inline-flex items-center justify-center rounded-[var(--radius-sm)] bg-[var(--color-brand-primary)] px-4 py-2.5 text-sm font-semibold text-[var(--color-text-inverse)] hover:bg-[var(--color-brand-primary-hover)] transition-colors"
                  >
                    View Syllabus &amp; Details →
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}