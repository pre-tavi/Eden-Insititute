import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  ProgressBar,
  Skeleton,
} from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { ensureCsrfToken, extractApiErrorMessage } from "../types/auth";
import {
  formatDurationSeconds,
  formatUtcInStudentTimezone,
  type CourseClassroomPayload,
  type LessonClassroomItem,
  type LiveSessionJoinResponse,
  type PlaybackTokenResponse,
} from "../types/classroom";

export function ClassroomPage() {
  const { slug } = useParams<{ slug: string }>();
  const { user } = useAuth();

  const [classroom, setClassroom] = useState<CourseClassroomPayload | null>(
    null
  );
  const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null);
  const [playbackToken, setPlaybackToken] =
    useState<PlaybackTokenResponse | null>(null);
  const [currentPositionS, setCurrentPositionS] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isTokenLoading, setIsTokenLoading] = useState<boolean>(false);
  const [isSavingProgress, setIsSavingProgress] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const studentTimezone =
    user?.profile?.timezone ||
    (typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone || "Africa/Nairobi"
      : "Africa/Nairobi");

  const fetchClassroom = useCallback(
    async (preserveSelection = false) => {
      if (!slug) {
        setErrorMessage("Missing course slug.");
        setIsLoading(false);
        return;
      }

      if (!preserveSelection) {
        setIsLoading(true);
      }
      setErrorMessage(null);

      try {
        const response = await fetch(
          `/api/classroom/courses/${encodeURIComponent(slug)}/`,
          {
            method: "GET",
            headers: { Accept: "application/json" },
            credentials: "same-origin",
          }
        );

        const payload: unknown = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(
            extractApiErrorMessage(
              payload,
              `Unable to open classroom (HTTP ${response.status}).`
            )
          );
        }

        const data = payload as CourseClassroomPayload;
        setClassroom(data);

        if (!preserveSelection) {
          const allLessons = data.modules.flatMap((m) => m.lessons);
          const resumeCandidate =
            allLessons.find((l) => l.progress.status === "in_progress") ??
            allLessons.find((l) => l.progress.status !== "completed") ??
            allLessons[0] ??
            null;

          if (resumeCandidate) {
            setSelectedLessonId(resumeCandidate.id);
            setCurrentPositionS(resumeCandidate.progress.last_position_s);
          }
        }
      } catch (err) {
        setErrorMessage(
          err instanceof Error ? err.message : "Failed to load classroom."
        );
      } finally {
        setIsLoading(false);
      }
    },
    [slug]
  );

  useEffect(() => {
    void fetchClassroom(false);
  }, [fetchClassroom]);

  const activeLesson: LessonClassroomItem | null = useMemo(() => {
    if (!classroom || !selectedLessonId) {
      return null;
    }
    for (const mod of classroom.modules) {
      const found = mod.lessons.find((l) => l.id === selectedLessonId);
      if (found) {
        return found;
      }
    }
    return null;
  }, [classroom, selectedLessonId]);

  const requestSignedPlaybackToken = useCallback(async (lessonId: string) => {
    setIsTokenLoading(true);
    setPlaybackToken(null);

    try {
      const csrfToken = await ensureCsrfToken();
      const response = await fetch(
        `/api/classroom/lessons/${encodeURIComponent(lessonId)}/playback-token/`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
            "X-CSRFToken": csrfToken,
          },
          credentials: "same-origin",
        }
      );

      const data: unknown = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          extractApiErrorMessage(
            data,
            "Could not obtain signed video playback token."
          )
        );
      }

      setPlaybackToken(data as PlaybackTokenResponse);
    } catch (err) {
      setActionNotice(
        err instanceof Error ? err.message : "Video token request failed."
      );
    } finally {
      setIsTokenLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeLesson && activeLesson.has_video) {
      void requestSignedPlaybackToken(activeLesson.id);
    } else {
      setPlaybackToken(null);
    }
  }, [activeLesson, requestSignedPlaybackToken]);

  const handleSelectLesson = (lesson: LessonClassroomItem) => {
    setSelectedLessonId(lesson.id);
    setCurrentPositionS(lesson.progress.last_position_s);
    setActionNotice(null);
  };

  const handleSaveProgress = async (
    nextPositionS: number,
    markCompleted = false
  ) => {
    if (!activeLesson) {
      return;
    }

    setIsSavingProgress(true);
    setActionNotice(null);

    try {
      const csrfToken = await ensureCsrfToken();
      const response = await fetch(
        `/api/classroom/lessons/${encodeURIComponent(activeLesson.id)}/progress/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-CSRFToken": csrfToken,
          },
          credentials: "same-origin",
          body: JSON.stringify({
            last_position_s: nextPositionS,
            mark_completed: markCompleted,
          }),
        }
      );

      const data: unknown = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          extractApiErrorMessage(data, "Failed to save lesson progress.")
        );
      }

      setCurrentPositionS(nextPositionS);
      await fetchClassroom(true);
      setActionNotice(
        markCompleted ||
          nextPositionS >= Math.floor(activeLesson.duration_seconds * 0.9)
          ? "Lesson reached >= 90% threshold and is marked COMPLETED."
          : `Saved resume position at ${formatDurationSeconds(nextPositionS)}.`
      );
    } catch (err) {
      setActionNotice(
        err instanceof Error ? err.message : "Unable to update progress."
      );
    } finally {
      setIsSavingProgress(false);
    }
  };

  const handleJoinLiveSession = async (sessionId: string) => {
    setActionNotice(null);
    try {
      const response = await fetch(
        `/api/classroom/live-sessions/${encodeURIComponent(sessionId)}/join/`,
        {
          method: "GET",
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        }
      );

      const data: unknown = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          extractApiErrorMessage(data, "Live lecture link is currently locked.")
        );
      }

      const joinData = data as LiveSessionJoinResponse;
      window.open(joinData.meet_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setActionNotice(
        err instanceof Error ? err.message : "Could not open Google Meet link."
      );
    }
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-10 space-y-6">
        <Skeleton className="h-6 w-56" label="Loading classroom header" />
        <Skeleton className="h-12 w-2/3" label="Loading programme title" />
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <Skeleton className="h-96 w-full" label="Loading lesson player" />
          </div>
          <div className="lg:col-span-4 space-y-4">
            <Skeleton className="h-48 w-full" label="Loading module list" />
            <Skeleton className="h-48 w-full" label="Loading live sessions" />
          </div>
        </div>
      </div>
    );
  }

  if (errorMessage || !classroom) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-10 space-y-4">
        <ErrorState
          title="Classroom Access Restricted or Unavailable"
          message={
            errorMessage ??
            "An active, paid enrollment is required to enter this classroom."
          }
          onRetry={() => {
            void fetchClassroom(false);
          }}
        />
        <div>
          <Link
            to="/my-learning"
            className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)] underline"
          >
            ← Return to My Learning Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const ninetyPercentSeconds = activeLesson
    ? Math.floor(activeLesson.duration_seconds * 0.9)
    : 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
      {/* Top Breadcrumb & Course Completion Header */}
      <header className="border-b border-[var(--color-border-hairline)] pb-6">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-3">
          <Link
            to="/my-learning"
            className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)] hover:underline"
          >
            ← Back to My Learning
          </Link>
          <span className="font-clinical-mono text-xs text-[var(--color-text-muted)]">
            COHORT: {classroom.cohort_name} · TIMEZONE: {studentTimezone}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-end">
          <div className="lg:col-span-8">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <Badge level={classroom.course.level} />
              <Badge residency={classroom.course.residency} />
            </div>
            <h1 className="font-editorial text-3xl sm:text-4xl font-semibold text-[var(--color-text-primary)]">
              {classroom.course.title}
            </h1>
          </div>

          <div className="lg:col-span-4 rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] p-4">
            <ProgressBar
              value={classroom.completion_percentage}
              label={`Completed ${classroom.completed_lessons} of ${classroom.total_lessons} Lessons`}
            />
          </div>
        </div>
      </header>

      {actionNotice && (
        <div
          role="status"
          className="mt-6 rounded-[var(--radius-sm)] border border-[var(--color-badge-certificate-border)] bg-[var(--color-status-success-bg)] p-3.5 text-xs font-medium text-[var(--color-status-success-text)]"
        >
          {actionNotice}
        </div>
      )}

      {/* Main Classroom Grid */}
      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-start">
        {/* Left Column: Protected Video Player + Reading Notes */}
        <div className="lg:col-span-8 space-y-6">
          {!activeLesson ? (
            <EmptyState
              title="No Published Lessons Yet"
              description="Dr. Violet is preparing the module recordings for this cohort."
            />
          ) : (
            <Card
              as="section"
              specLabel={`LESSON 0${activeLesson.order} // ${activeLesson.kind.toUpperCase()}`}
              specCode={`STATUS: ${activeLesson.progress.status.toUpperCase()}`}
            >
              <div className="p-5 sm:p-6 space-y-5">
                <div>
                  <h2 className="font-editorial text-2xl font-semibold text-[var(--color-text-primary)]">
                    {activeLesson.title}
                  </h2>
                  <p className="mt-1 font-clinical-mono text-xs text-[var(--color-text-muted)]">
                    Duration: {formatDurationSeconds(activeLesson.duration_seconds)} ·
                    Resume Position: {formatDurationSeconds(currentPositionS)} ·
                    90% Completion Gate: {formatDurationSeconds(ninetyPercentSeconds)}
                  </p>
                </div>

                {/* Protected Signed Video Viewport with Faint Student Email Deterrent Overlay */}
                {activeLesson.has_video && (
                  <div className="relative overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border-strong)] bg-[#0c1915] text-[var(--color-text-inverse)] p-6 sm:p-8 min-h-[260px] flex flex-col justify-between">
                    {/* Faint Deterrent Watermark Overlay (Blueprint Phase 4) */}
                    <div
                      aria-hidden="true"
                      className="pointer-events-none select-none absolute inset-0 flex items-center justify-center opacity-15"
                    >
                      <span className="-rotate-12 font-clinical-mono text-lg sm:text-2xl font-semibold tracking-widest text-white">
                        {playbackToken?.watermark_email || user?.email}
                      </span>
                    </div>

                    <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 border-b border-white/15 pb-3 font-clinical-mono text-xs">
                      <span className="text-emerald-300">
                        ● MANAGED VIDEO STREAM (SIGNED TOKEN VERIFIED)
                      </span>
                      <span>
                        {isTokenLoading
                          ? "Issuing short-lived token…"
                          : playbackToken
                          ? `EXPIRES: ${formatUtcInStudentTimezone(
                              playbackToken.expires_at,
                              studentTimezone
                            )}`
                          : "Token required"}
                      </span>
                    </div>

                    <div className="relative z-10 my-6 space-y-2">
                      <p className="font-editorial text-xl text-white">
                        {activeLesson.title}
                      </p>
                      <p className="font-clinical-mono text-xs text-slate-300 break-all">
                        Signed Playback Token:{" "}
                        {playbackToken
                          ? `${playbackToken.playback_token.slice(0, 44)}…`
                          : " requesting…"}
                      </p>
                    </div>

                    {/* Playback Scrubber & 90% Completion Trigger Controls */}
                    <div className="relative z-10 space-y-3 border-t border-white/15 pt-4">
                      <div className="flex items-center justify-between font-clinical-mono text-xs text-slate-200">
                        <span>
                          Position: {formatDurationSeconds(currentPositionS)}
                        </span>
                        <span>
                          Total: {formatDurationSeconds(activeLesson.duration_seconds)}
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          isLoading={isSavingProgress}
                          onClick={() => {
                            const nextPos = Math.min(
                              activeLesson.duration_seconds,
                              currentPositionS + 300
                            );
                            void handleSaveProgress(nextPos, false);
                          }}
                        >
                          Save Resume (+5m)
                        </Button>
                        <Button
                          size="sm"
                          isLoading={isSavingProgress}
                          onClick={() => {
                            void handleSaveProgress(ninetyPercentSeconds, false);
                          }}
                        >
                          Reach 90% &amp; Complete Lesson ✓
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Clinical Reading & Lecture Notes */}
                {activeLesson.reading_body && (
                  <div className="rounded-[var(--radius-sm)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-subtle)] p-4 text-sm text-[var(--color-text-secondary)] whitespace-pre-line">
                    <p className="mb-2 font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-text-primary)]">
                      Dr. Violet&apos;s Lecture Notes &amp; Clinical Guidance
                    </p>
                    {activeLesson.reading_body}
                  </div>
                )}

                {!activeLesson.has_video && (
                  <div className="flex justify-end">
                    <Button
                      size="sm"
                      isLoading={isSavingProgress}
                      onClick={() => {
                        void handleSaveProgress(
                          activeLesson.duration_seconds,
                          true
                        );
                      }}
                    >
                      Mark Reading Complete ✓
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Live Google Meet Sessions Schedule (Rendered in Student Timezone) */}
          <Card
            as="section"
            specLabel="SYNCHRONOUS GOOGLE MEET LECTURES"
            specCode={`TIMEZONE // ${studentTimezone.toUpperCase()}`}
          >
            <div className="p-5 sm:p-6 space-y-4">
              <div>
                <h2 className="font-editorial text-2xl font-semibold text-[var(--color-text-primary)]">
                  Live Cohort Lectures
                </h2>
                <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                  All session times are converted from UTC into your local timezone (
                  <strong>{studentTimezone}</strong>). Google Meet links unlock 30 minutes before
                  start time for active students.
                </p>
              </div>

              {classroom.live_sessions.length === 0 ? (
                <p className="text-sm text-[var(--color-text-secondary)]">
                  No live sessions scheduled yet for this cohort.
                </p>
              ) : (
                <ul className="divide-y divide-[var(--color-border-hairline)]">
                  {classroom.live_sessions.map((session) => (
                    <li
                      key={session.id}
                      className="py-3.5 first:pt-0 last:pb-0 flex flex-wrap items-center justify-between gap-4"
                    >
                      <div>
                        <p className="font-semibold text-sm text-[var(--color-text-primary)]">
                          {session.title}
                        </p>
                        <p className="font-clinical-mono text-xs text-[var(--color-text-muted)]">
                          Local Time:{" "}
                          {formatUtcInStudentTimezone(
                            session.starts_at,
                            studentTimezone
                          )}{" "}
                          ({session.duration_minutes} mins)
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        {session.recording_lesson_id && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => {
                              const rec = classroom.modules
                                .flatMap((m) => m.lessons)
                                .find(
                                  (l) => l.id === session.recording_lesson_id
                                );
                              if (rec) {
                                handleSelectLesson(rec);
                              }
                            }}
                          >
                            Watch Recording
                          </Button>
                        )}
                        <Button
                          size="sm"
                          disabled={!session.join_window_open}
                          onClick={() => {
                            void handleJoinLiveSession(session.id);
                          }}
                        >
                          {session.join_window_open
                            ? "Join Google Meet →"
                            : "Meet Link Unlocks 30m Prior"}
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </Card>
        </div>

        {/* Right Column: Ordered Modules & Lessons Navigator */}
        <Card
          as="aside"
          specLabel="COURSE MODULES & PROGRESS"
          specCode={`${classroom.completed_lessons}/${classroom.total_lessons} DONE`}
          className="lg:col-span-4"
        >
          <div className="p-5 space-y-5">
            {classroom.modules.map((mod) => (
              <div key={mod.id} className="space-y-2">
                <h3 className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)]">
                  Module 0{mod.order}: {mod.title}
                </h3>
                <ul className="space-y-1.5">
                  {mod.lessons.map((lesson) => {
                    const isSelected = lesson.id === activeLesson?.id;
                    const isCompleted = lesson.progress.status === "completed";

                    return (
                      <li key={lesson.id}>
                        <button
                          type="button"
                          onClick={() => handleSelectLesson(lesson)}
                          className={[
                            "w-full text-left rounded-[var(--radius-sm)] border px-3 py-2.5 text-xs transition-colors flex items-start justify-between gap-2",
                            isSelected
                              ? "border-[var(--color-brand-primary)] bg-[var(--color-bg-subtle)] font-semibold text-[var(--color-text-primary)]"
                              : "border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-subtle)]",
                          ].join(" ")}
                        >
                          <span>
                            {lesson.order}. {lesson.title}
                          </span>
                          <span className="font-clinical-mono text-[11px] shrink-0">
                            {isCompleted
                              ? "✓ DONE"
                              : lesson.progress.last_position_s > 0
                              ? `${formatDurationSeconds(
                                  lesson.progress.last_position_s
                                )}`
                              : formatDurationSeconds(lesson.duration_seconds)}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}