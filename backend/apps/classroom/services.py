"""
Classroom Security & Progress Services for Dr. Violet's LMS (EdenLMS):
1. Active Enrollment Authorization Gate (`user_has_active_course_enrollment`).
2. Short-lived HMAC-SHA256 Signed Playback Token Generator (`issue_signed_playback_token`).
3. 90% Threshold Progress Recorder (`update_student_lesson_progress`).
"""
import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.catalog.models import Course
from apps.enrollments.models import Enrollment

from .models import Lesson, LessonProgress


def get_active_enrollment_for_course(user, course: Course) -> Enrollment | None:
    """
    Return the student's ACTIVE or COMPLETED Enrollment for the given Course, or None.
    Pending, withdrawn, or refunded enrollments do not grant classroom access.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return None

    return (
        Enrollment.objects.for_user(user)
        .filter(
            cohort__course=course,
            status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED],
        )
        .select_related("cohort", "cohort__course")
        .first()
    )


def require_active_enrollment_for_course(user, course: Course) -> Enrollment:
    """Raise DRF PermissionDenied (403) if the student does not hold an active enrollment."""
    enrollment = get_active_enrollment_for_course(user, course)
    if enrollment is None:
        raise PermissionDenied(
            "An active, paid enrollment in this course is required to access classroom materials."
        )
    return enrollment


def issue_signed_playback_token(*, user, lesson: Lesson) -> dict:
    """
    Issue a short-lived HMAC-SHA256 signed video playback token tied to the student, lesson,
    expiry timestamp, and domain restriction.
    - Verifies the student has an ACTIVE (or COMPLETED) enrollment in `lesson.module.course`.
    - Never exposes the raw `lesson.video_asset_id` in public responses; encodes a signed payload
      with the student's email for faint video watermarking deterrence.
    """
    course = lesson.module.course
    require_active_enrollment_for_course(user, course)

    ttl_seconds = int(getattr(settings, "VIDEO_TOKEN_TTL_SECONDS", 3600))
    signing_secret = (
        getattr(settings, "VIDEO_SIGNING_SECRET", "").strip()
        or settings.SECRET_KEY
    )

    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(seconds=ttl_seconds)

    # Derive an opaque playback stream handle so the raw provider asset ID is never exposed directly
    asset_digest = hashlib.sha256(
        f"{lesson.id}:{lesson.video_asset_id}:{signing_secret}".encode()
    ).hexdigest()[:24]

    claims = {
        "sub": str(user.id),
        "lesson_id": str(lesson.id),
        "stream_handle": f"stream_{asset_digest}",
        "watermark": user.email,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    payload_bytes = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")

    signature = hmac.new(
        signing_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()

    signed_token = f"{payload_b64}.{signature}"

    return {
        "lesson_id": str(lesson.id),
        "playback_token": signed_token,
        "expires_at": expires_at.isoformat(),
        "watermark_email": user.email,
        "duration_seconds": lesson.duration_seconds,
    }


@transaction.atomic
def update_student_lesson_progress(
    *,
    user,
    lesson: Lesson,
    position_seconds: int,
    mark_completed: bool = False,
) -> LessonProgress:
    """
    Update `last_position_s` for the student's lesson and automatically mark `COMPLETED`
    once playback reaches >= 90% of `lesson.duration_seconds` (or if `mark_completed=True`).
    """
    course = lesson.module.course
    require_active_enrollment_for_course(user, course)

    clamped_position = max(0, min(position_seconds, max(lesson.duration_seconds, position_seconds)))
    threshold_seconds = int(lesson.duration_seconds * 0.9) if lesson.duration_seconds > 0 else 0
    reached_ninety_percent = lesson.duration_seconds > 0 and clamped_position >= threshold_seconds

    progress, _ = LessonProgress.objects.select_for_update().get_or_create(
        user=user,
        lesson=lesson,
        defaults={
            "status": LessonProgress.Status.IN_PROGRESS,
            "last_position_s": clamped_position,
        },
    )

    progress.last_position_s = clamped_position

    if mark_completed or reached_ninety_percent:
        progress.status = LessonProgress.Status.COMPLETED
        if progress.completed_at is None:
            progress.completed_at = timezone.now()
    elif progress.status == LessonProgress.Status.NOT_STARTED and clamped_position > 0:
        progress.status = LessonProgress.Status.IN_PROGRESS

    progress.save(update_fields=["status", "last_position_s", "completed_at", "updated_at"])
    return progress