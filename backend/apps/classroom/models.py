"""
Classroom domain models for Dr. Violet's LMS (EdenLMS):
Module, Lesson, LiveSession, and LessonProgress.
Complies with Blueprint Section 4 & Phase 4 and Pre-Deployment Security Checklist #17 & #23:
- Video lives on a managed video host (video_asset_id is a provider ID, never a raw public URL).
- LiveSession stores starts_at in UTC and protects meet_url behind active enrollment + join window checks.
"""
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.catalog.models import Cohort, Course


class Module(models.Model):
    """Ordered curriculum module within a Course."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules",
    )
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "classroom_module"
        ordering = ["order", "created_at"]
        verbose_name = "module"
        verbose_name_plural = "modules"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"],
                name="unique_course_module_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course.title} — Module {self.order}: {self.title}"


class Lesson(models.Model):
    """
    Individual learning unit inside a Module.
    video_asset_id stores the managed video host's asset identifier and is NEVER exposed in public APIs.
    """

    class Kind(models.TextChoices):
        VIDEO = "video", "Protected Video Playback"
        READING = "reading", "Clinical Reading / Case Notes"
        LIVE = "live", "Live Lecture Companion"
        QUIZ = "quiz", "Self-Assessment Check"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        default=Kind.VIDEO,
        db_index=True,
    )
    duration_seconds = models.PositiveIntegerField(
        default=1800,
        help_text="Total duration in seconds (used to trigger 90% completion threshold).",
    )
    video_asset_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="Managed video host asset ID (never exposed in public or unpaid student responses).",
    )
    reading_body = models.TextField(
        blank=True,
        help_text="Plain/Markdown clinical reading notes for reading or video lessons.",
    )
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "classroom_lesson"
        ordering = ["module__order", "order"]
        verbose_name = "lesson"
        verbose_name_plural = "lessons"
        constraints = [
            models.UniqueConstraint(
                fields=["module", "order"],
                name="unique_module_lesson_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.module.title} — Lesson {self.order}: {self.title} ({self.kind})"


class LiveSession(models.Model):
    """
    Scheduled synchronous Google Meet lecture for a Cohort.
    - starts_at is stored strictly in UTC.
    - meet_url is NEVER returned in public responses; it is revealed only to students with an
      ACTIVE enrollment and only within the join window (30 minutes before start through end).
    - recording_lesson links to the recorded Lesson playback once Dr. Violet attaches it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="live_sessions",
    )
    title = models.CharField(max_length=200)
    starts_at = models.DateTimeField(
        db_index=True,
        help_text="Lecture start timestamp in UTC.",
    )
    duration_minutes = models.PositiveIntegerField(default=90)
    meet_url = models.URLField(
        max_length=500,
        help_text="Google Meet link (protected; only revealed to active students within join window).",
    )
    recording_lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_from_sessions",
        help_text="Optional recorded video lesson attached after the live lecture finishes.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "classroom_livesession"
        ordering = ["starts_at"]
        verbose_name = "live session"
        verbose_name_plural = "live sessions"

    def __str__(self) -> str:
        return f"{self.cohort.name} — {self.title} ({self.starts_at.isoformat()})"

    def is_within_join_window(self, now=None) -> bool:
        """
        Return True if `now` falls within [starts_at - 30 minutes, starts_at + duration_minutes + 30 minutes].
        """
        current_time = now or timezone.now()
        window_open = self.starts_at - timedelta(minutes=30)
        window_close = self.starts_at + timedelta(minutes=self.duration_minutes + 30)
        return window_open <= current_time <= window_close


class LessonProgressQuerySet(models.QuerySet):
    """Custom QuerySet enforcing per-student record isolation."""

    def for_user(self, user) -> "LessonProgressQuerySet":
        if not user or not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(user=user)


class LessonProgressManager(models.Manager.from_queryset(LessonProgressQuerySet)):
    """Default manager exposing .for_user(request.user) on LessonProgress.objects."""


class LessonProgress(models.Model):
    """
    Tracks a student's resume position (`last_position_s`) and completion status per Lesson.
    Automatically marks `status = COMPLETED` when `last_position_s >= 90%` of `lesson.duration_seconds`.
    """

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="student_progress",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
        db_index=True,
    )
    last_position_s = models.PositiveIntegerField(
        default=0,
        help_text="Last playback position in seconds for seamless resume.",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LessonProgressManager()

    class Meta:
        db_table = "classroom_lessonprogress"
        verbose_name = "lesson progress"
        verbose_name_plural = "lesson progress records"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "lesson"],
                name="unique_student_lesson_progress",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.last_position_s < 0:
            raise ValidationError({"last_position_s": "Playback position cannot be negative."})

    def __str__(self) -> str:
        return f"{self.user.email} — {self.lesson.title}: {self.status} ({self.last_position_s}s)"