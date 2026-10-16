"""
Trimmed, security-hardened serializers for the Student Classroom experience.
Complies with Pre-Deployment Security Checklist #17 & #23:
- Never exposes Lesson.video_asset_id in any API response.
- Never exposes LiveSession.meet_url in list responses; meet_url is only returned via the
  dedicated join endpoint when the student holds an ACTIVE enrollment and is inside the join window.
"""
from rest_framework import serializers

from .models import Lesson, LessonProgress, LiveSession, Module


class LessonProgressSerializer(serializers.ModelSerializer):
    """Serializes a student's saved resume position and completion status for a Lesson."""

    class Meta:
        model = LessonProgress
        fields = (
            "id",
            "lesson",
            "status",
            "last_position_s",
            "completed_at",
            "updated_at",
        )
        read_only_fields = fields


class LessonProgressUpdateSerializer(serializers.Serializer):
    """Validates a student's progress update request (`last_position_s` and optional `completed`)."""

    last_position_s = serializers.IntegerField(min_value=0, max_value=86400)
    mark_completed = serializers.BooleanField(default=False, required=False)


class LessonClassroomSerializer(serializers.ModelSerializer):
    """
    Serializes a Lesson for an enrolled student without ever exposing `video_asset_id`.
    Embeds the requesting student's personal progress (`last_position_s` and `status`).
    """

    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    has_video = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            "id",
            "order",
            "title",
            "kind",
            "kind_display",
            "duration_seconds",
            "reading_body",
            "has_video",
            "progress",
        )
        read_only_fields = fields

    def get_has_video(self, obj: Lesson) -> bool:
        return bool(obj.video_asset_id and obj.kind == Lesson.Kind.VIDEO)

    def get_progress(self, obj: Lesson) -> dict:
        progress_map: dict = self.context.get("progress_map", {})
        record: LessonProgress | None = progress_map.get(obj.id)
        if record is None:
            return {
                "status": LessonProgress.Status.NOT_STARTED,
                "last_position_s": 0,
                "completed_at": None,
            }
        return {
            "status": record.status,
            "last_position_s": record.last_position_s,
            "completed_at": record.completed_at,
        }


class ModuleClassroomSerializer(serializers.ModelSerializer):
    """Serializes a Course Module and its published Lessons for an active student."""

    lessons = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = (
            "id",
            "order",
            "title",
            "description",
            "lessons",
        )
        read_only_fields = fields

    def get_lessons(self, obj: Module) -> list[dict]:
        published_lessons = [lesson for lesson in obj.lessons.all() if lesson.is_published]
        return LessonClassroomSerializer(
            published_lessons,
            many=True,
            context=self.context,
        ).data


class LiveSessionClassroomSerializer(serializers.ModelSerializer):
    """
    Serializes scheduled LiveSessions for an active student's cohort.
    Note: `meet_url` is intentionally omitted here and only returned inside the join window
    or via the dedicated join endpoint so future links cannot be scraped in advance.
    """

    join_window_open = serializers.SerializerMethodField()
    recording_lesson_id = serializers.UUIDField(source="recording_lesson.id", read_only=True, allow_null=True)

    class Meta:
        model = LiveSession
        fields = (
            "id",
            "title",
            "starts_at",
            "duration_minutes",
            "join_window_open",
            "recording_lesson_id",
        )
        read_only_fields = fields

    def get_join_window_open(self, obj: LiveSession) -> bool:
        return obj.is_within_join_window()