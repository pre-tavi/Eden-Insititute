"""
Phase 4 Classroom, Signed Video Playback, Progress & Live Session Test Suite.
Verifies:
1. Unpaid (`pending_payment`) or unenrolled students CANNOT obtain a playback token (403)
   or access the classroom overview (403).
2. Raw `video_asset_id` and `meet_url` are never exposed in classroom overview JSON responses.
3. Active students CAN obtain a short-lived signed playback token with watermark email.
4. Lesson progress (`last_position_s`) persists across requests and automatically marks
   `status = COMPLETED` at >= 90% of `duration_seconds`.
5. LiveSession `meet_url` is unlocked ONLY for active students within the join window.
"""
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.catalog.models import Cohort, Course, Price
from apps.classroom.models import Lesson, LessonProgress, LiveSession, Module
from apps.enrollments.models import Enrollment, activate_enrollment

User = get_user_model()


@pytest.fixture
def classroom_setup():
    course = Course.objects.create(
        title="Certificate in Counselling Psychology",
        slug="cert-counselling-classroom-test",
        summary="Weekly live lectures + protected video playbacks.",
        level=Course.Level.CERTIFICATE,
        residency=Course.Residency.OPTIONAL,
        status=Course.Status.PUBLISHED,
    )
    Price.objects.create(
        course=course,
        audience=Price.Audience.LOCAL,
        currency=Price.Currency.KES,
        amount_minor=3_500_000,
    )
    cohort = Cohort.objects.create(
        course=course,
        name="January 2027 Intake",
        starts_on=date(2027, 1, 15),
        capacity=30,
        enrollment_open=True,
    )
    module = Module.objects.create(
        course=course,
        order=1,
        title="Module 1: Clinical Ethics",
    )
    video_lesson = Lesson.objects.create(
        module=module,
        order=1,
        title="Lesson 1: Confidentiality & Consent",
        kind=Lesson.Kind.VIDEO,
        duration_seconds=1000,
        video_asset_id="SECRET_PROVIDER_ASSET_ID_999",
        reading_body="Clinical reading notes.",
        is_published=True,
    )
    live_session_open = LiveSession.objects.create(
        cohort=cohort,
        title="Live Seminar (Within Join Window)",
        starts_at=timezone.now() + timedelta(minutes=15),
        duration_minutes=90,
        meet_url="https://meet.google.com/secret-cohort-link",
        recording_lesson=video_lesson,
    )
    live_session_future = LiveSession.objects.create(
        cohort=cohort,
        title="Live Seminar (Next Week - Locked)",
        starts_at=timezone.now() + timedelta(days=7),
        duration_minutes=90,
        meet_url="https://meet.google.com/future-locked-link",
    )

    unpaid_student = User.objects.create_user(
        email="unpaid@example.com",
        password="StrongPassword!2026",
    )
    Profile.objects.create(user=unpaid_student, display_name="Unpaid Student", country="KE")
    Enrollment.objects.create(
        user=unpaid_student,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )

    active_student = User.objects.create_user(
        email="active@example.com",
        password="StrongPassword!2026",
    )
    Profile.objects.create(user=active_student, display_name="Active Student", country="KE")
    active_enrollment = Enrollment.objects.create(
        user=active_student,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )
    activate_enrollment(active_enrollment, source="test_verified")

    return {
        "course": course,
        "video_lesson": video_lesson,
        "live_session_open": live_session_open,
        "live_session_future": live_session_future,
        "unpaid_student": unpaid_student,
        "active_student": active_student,
    }


@pytest.mark.django_db
def test_unpaid_student_cannot_obtain_playback_token_or_enter_classroom(classroom_setup):
    """Phase 4 Gate: An unpaid (pending_payment) student cannot obtain a playback token (403)."""
    client = APIClient()
    client.force_authenticate(user=classroom_setup["unpaid_student"])

    overview_res = client.get(
        reverse(
            "classroom:course-classroom",
            kwargs={"slug": classroom_setup["course"].slug},
        )
    )
    assert overview_res.status_code == 403

    token_res = client.post(
        reverse(
            "classroom:lesson-playback-token",
            kwargs={"lesson_id": classroom_setup["video_lesson"].id},
        )
    )
    assert token_res.status_code == 403

    join_res = client.get(
        reverse(
            "classroom:live-session-join",
            kwargs={"session_id": classroom_setup["live_session_open"].id},
        )
    )
    assert join_res.status_code == 403


@pytest.mark.django_db
def test_active_student_receives_signed_token_and_progress_survives_refresh(classroom_setup):
    """
    Phase 4 Gate:
    - Raw `video_asset_id` and `meet_url` never leak in classroom overview JSON.
    - Active student receives short-lived signed playback token with watermark email.
    - Progress (`last_position_s`) survives refresh and marks COMPLETED at >= 90%.
    """
    client = APIClient()
    active_student = classroom_setup["active_student"]
    video_lesson = classroom_setup["video_lesson"]
    course = classroom_setup["course"]
    client.force_authenticate(user=active_student)

    # 1. Fetch classroom overview and verify sensitive fields are trimmed
    overview_res = client.get(
        reverse("classroom:course-classroom", kwargs={"slug": course.slug})
    )
    assert overview_res.status_code == 200
    raw_json_str = overview_res.content.decode("utf-8")
    assert "SECRET_PROVIDER_ASSET_ID_999" not in raw_json_str
    assert "https://meet.google.com/secret-cohort-link" not in raw_json_str

    # 2. Request signed playback token
    token_res = client.post(
        reverse(
            "classroom:lesson-playback-token",
            kwargs={"lesson_id": video_lesson.id},
        )
    )
    assert token_res.status_code == 200
    token_data = token_res.json()
    assert "." in token_data["playback_token"]
    assert token_data["watermark_email"] == "active@example.com"
    assert "SECRET_PROVIDER_ASSET_ID_999" not in token_data["playback_token"]

    # 3. Save partial playback position (450s / 1000s = 45%) -> IN_PROGRESS
    progress_url = reverse(
        "classroom:lesson-progress",
        kwargs={"lesson_id": video_lesson.id},
    )
    partial_res = client.post(
        progress_url,
        {"last_position_s": 450},
        format="json",
    )
    assert partial_res.status_code == 200
    assert partial_res.json()["status"] == LessonProgress.Status.IN_PROGRESS
    assert partial_res.json()["last_position_s"] == 450

    # Verify progress survives a fresh classroom GET (refresh)
    refreshed = client.get(
        reverse("classroom:course-classroom", kwargs={"slug": course.slug})
    ).json()
    lesson_state = refreshed["modules"][0]["lessons"][0]["progress"]
    assert lesson_state["last_position_s"] == 450
    assert lesson_state["status"] == LessonProgress.Status.IN_PROGRESS
    assert refreshed["completion_percentage"] == 0

    # 4. Advance playback to 900s / 1000s (90%) -> automatically marks COMPLETED
    complete_res = client.post(
        progress_url,
        {"last_position_s": 900},
        format="json",
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == LessonProgress.Status.COMPLETED
    assert complete_res.json()["completed_at"] is not None

    refreshed_after = client.get(
        reverse("classroom:course-classroom", kwargs={"slug": course.slug})
    ).json()
    assert refreshed_after["completion_percentage"] == 100


@pytest.mark.django_db
def test_live_session_meet_url_enforces_join_window(classroom_setup):
    """Verify meet_url is returned within the join window and blocked (403) outside it."""
    client = APIClient()
    client.force_authenticate(user=classroom_setup["active_student"])

    open_join = client.get(
        reverse(
            "classroom:live-session-join",
            kwargs={"session_id": classroom_setup["live_session_open"].id},
        )
    )
    assert open_join.status_code == 200
    assert open_join.json()["meet_url"] == "https://meet.google.com/secret-cohort-link"

    future_join = client.get(
        reverse(
            "classroom:live-session-join",
            kwargs={"session_id": classroom_setup["live_session_future"].id},
        )
    )
    assert future_join.status_code == 403