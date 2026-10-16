"""
Authenticated Classroom API views for Dr. Violet's LMS (EdenLMS):
- Course Classroom Overview (modules, lessons, per-lesson progress, completion percentage, live sessions)
- Short-Lived Signed Video Playback Token endpoint (ACTIVE students only)
- Lesson Progress Upsert endpoint (resume from `last_position_s`, auto-complete at 90%)
- LiveSession Google Meet Join endpoint (ACTIVE students only, within the join window)
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Course

from .models import Lesson, LessonProgress, LiveSession, Module
from .serializers import (
    LessonProgressSerializer,
    LessonProgressUpdateSerializer,
    LiveSessionClassroomSerializer,
    ModuleClassroomSerializer,
)
from .services import (
    issue_signed_playback_token,
    require_active_enrollment_for_course,
    update_student_lesson_progress,
)


class CourseClassroomView(APIView):
    """
    GET /api/classroom/courses/<slug:slug>/
    Returns the complete classroom state for a student with an ACTIVE enrollment:
    modules, lessons (without video_asset_id), saved progress, overall completion percentage,
    and upcoming/recorded live sessions in UTC.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, slug: str) -> Response:
        course = get_object_or_404(
            Course.objects.filter(status=Course.Status.PUBLISHED),
            slug=slug,
        )
        enrollment = require_active_enrollment_for_course(request.user, course)

        modules = (
            Module.objects.filter(course=course)
            .prefetch_related("lessons")
            .order_by("order")
        )

        progress_records = LessonProgress.objects.for_user(request.user).filter(
            lesson__module__course=course
        )
        progress_map = {record.lesson_id: record for record in progress_records}

        total_lessons = 0
        completed_lessons = 0
        for mod in modules:
            for lesson in mod.lessons.all():
                if lesson.is_published:
                    total_lessons += 1
                    rec = progress_map.get(lesson.id)
                    if rec and rec.status == LessonProgress.Status.COMPLETED:
                        completed_lessons += 1

        completion_percentage = (
            round((completed_lessons / total_lessons) * 100)
            if total_lessons > 0
            else 0
        )

        live_sessions = LiveSession.objects.filter(
            cohort=enrollment.cohort
        ).select_related("recording_lesson").order_by("starts_at")

        context = {"request": request, "progress_map": progress_map}

        return Response(
            {
                "course": {
                    "id": str(course.id),
                    "title": course.title,
                    "slug": course.slug,
                    "level": course.level,
                    "residency": course.residency,
                },
                "enrollment_id": str(enrollment.id),
                "cohort_name": enrollment.cohort.name,
                "completion_percentage": completion_percentage,
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "modules": ModuleClassroomSerializer(
                    modules, many=True, context=context
                ).data,
                "live_sessions": LiveSessionClassroomSerializer(
                    live_sessions, many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class LessonPlaybackTokenView(APIView):
    """
    POST /api/classroom/lessons/<uuid:lesson_id>/playback-token/
    Issues a short-lived signed playback token only to students with an ACTIVE enrollment.
    Unpaid/pending students receive 403 Forbidden.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, lesson_id) -> Response:
        lesson = get_object_or_404(
            Lesson.objects.select_related("module__course").filter(is_published=True),
            pk=lesson_id,
        )
        token_payload = issue_signed_playback_token(
            user=request.user,
            lesson=lesson,
        )
        return Response(token_payload, status=status.HTTP_200_OK)


class LessonProgressUpdateView(APIView):
    """
    POST /api/classroom/lessons/<uuid:lesson_id>/progress/
    Saves `last_position_s` and marks complete automatically at >= 90% duration.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, lesson_id) -> Response:
        lesson = get_object_or_404(
            Lesson.objects.select_related("module__course").filter(is_published=True),
            pk=lesson_id,
        )
        serializer = LessonProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        progress = update_student_lesson_progress(
            user=request.user,
            lesson=lesson,
            position_seconds=serializer.validated_data["last_position_s"],
            mark_completed=serializer.validated_data.get("mark_completed", False),
        )
        return Response(
            LessonProgressSerializer(progress).data,
            status=status.HTTP_200_OK,
        )


class LiveSessionJoinView(APIView):
    """
    GET /api/classroom/live-sessions/<uuid:session_id>/join/
    Reveals the protected Google Meet URL (`meet_url`) ONLY to students with an ACTIVE
    enrollment in that cohort AND only within the join window.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, session_id) -> Response:
        live_session = get_object_or_404(
            LiveSession.objects.select_related("cohort__course"),
            pk=session_id,
        )
        enrollment = require_active_enrollment_for_course(
            request.user, live_session.cohort.course
        )

        if enrollment.cohort_id != live_session.cohort_id:
            return Response(
                {"detail": "You are not enrolled in the cohort for this live session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not live_session.is_within_join_window():
            return Response(
                {
                    "detail": (
                        "The Google Meet link is only unlocked 30 minutes before the "
                        "scheduled lecture start time."
                    ),
                    "starts_at": live_session.starts_at,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            {
                "id": str(live_session.id),
                "title": live_session.title,
                "starts_at": live_session.starts_at,
                "meet_url": live_session.meet_url,
            },
            status=status.HTTP_200_OK,
        )