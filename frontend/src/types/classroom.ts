/**
 * TypeScript contracts for Phase 4 Classroom, Signed Video Playback,
 * Per-Lesson Progress, and Live Google Meet Sessions.
 */
import type { CourseLevel, ResidencyMode } from "./catalog";

export type LessonKind = "video" | "reading" | "live" | "quiz";

export type LessonProgressStatus = "not_started" | "in_progress" | "completed";

export interface LessonProgressSummary {
  status: LessonProgressStatus;
  last_position_s: number;
  completed_at: string | null;
}

export interface LessonClassroomItem {
  id: string;
  order: number;
  title: string;
  kind: LessonKind;
  kind_display: string;
  duration_seconds: number;
  reading_body: string;
  has_video: boolean;
  progress: LessonProgressSummary;
}

export interface ModuleClassroomItem {
  id: string;
  order: number;
  title: string;
  description: string;
  lessons: LessonClassroomItem[];
}

export interface LiveSessionClassroomItem {
  id: string;
  title: string;
  starts_at: string;
  duration_minutes: number;
  join_window_open: boolean;
  recording_lesson_id: string | null;
}

export interface CourseClassroomPayload {
  course: {
    id: string;
    title: string;
    slug: string;
    level: CourseLevel;
    residency: ResidencyMode;
  };
  enrollment_id: string;
  cohort_name: string;
  completion_percentage: number;
  completed_lessons: number;
  total_lessons: number;
  modules: ModuleClassroomItem[];
  live_sessions: LiveSessionClassroomItem[];
}

export interface PlaybackTokenResponse {
  lesson_id: string;
  playback_token: string;
  expires_at: string;
  watermark_email: string;
  duration_seconds: number;
}

export interface LiveSessionJoinResponse {
  id: string;
  title: string;
  starts_at: string;
  meet_url: string;
}

/**
 * Formats seconds (e.g., 1800) into MM:SS or HH:MM:SS for the lesson player.
 */
export function formatDurationSeconds(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const seconds = safe % 60;

  const paddedMinutes = String(minutes).padStart(2, "0");
  const paddedSeconds = String(seconds).padStart(2, "0");

  if (hours > 0) {
    return `${hours}:${paddedMinutes}:${paddedSeconds}`;
  }
  return `${paddedMinutes}:${paddedSeconds}`;
}

/**
 * Formats a UTC ISO timestamp into the student's local IANA timezone.
 */
export function formatUtcInStudentTimezone(
  utcIsoString: string,
  timezone: string
): string {
  try {
    const date = new Date(utcIsoString);
    return new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: timezone,
    }).format(date);
  } catch {
    return utcIsoString;
  }
}