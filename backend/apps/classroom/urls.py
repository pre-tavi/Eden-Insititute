"""URL routes for the student classroom, signed video playback, and live sessions app."""
from django.urls import path

from .views import (
    CourseClassroomView,
    LessonPlaybackTokenView,
    LessonProgressUpdateView,
    LiveSessionJoinView,
)

app_name = "classroom"

urlpatterns = [
    path(
        "courses/<slug:slug>/",
        CourseClassroomView.as_view(),
        name="course-classroom",
    ),
    path(
        "lessons/<uuid:lesson_id>/playback-token/",
        LessonPlaybackTokenView.as_view(),
        name="lesson-playback-token",
    ),
    path(
        "lessons/<uuid:lesson_id>/progress/",
        LessonProgressUpdateView.as_view(),
        name="lesson-progress",
    ),
    path(
        "live-sessions/<uuid:session_id>/join/",
        LiveSessionJoinView.as_view(),
        name="live-session-join",
    ),
]