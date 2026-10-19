"""
Interactive Terminal Verification Suite for Phase 4 (Classroom & Video)
and Phase 5 (Nairobi & Embu Residency Blocks + Two-Browser Concurrency).
Run with: cd backend && pytest -s -v tests/test_p4_p5_interactive_verification.py
"""
import base64
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import close_old_connections
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.catalog.models import Cohort, Course, Price
from apps.classroom.models import Lesson, LessonProgress, LiveSession, Module
from apps.enrollments.admin import EnrollmentAdmin, mark_enrollments_active_manually
from apps.enrollments.models import Enrollment
from apps.residency.models import ResidencyBlock, ResidencyRegistration

User = get_user_model()


@pytest.mark.django_db
def test_phase_4_classroom_video_watermark_resume_autocomplete_and_live_window():
    """
    End-to-end terminal verification for Phase 4:
    1. Manually mark enrollment as paid in Django Admin to unlock classroom access.
    2. Video Watermark: Verify student email overlay in playback token response & signed claims.
    3. Resume Playback: Save at 15s, refresh classroom GET, verify resume from last_position_s=15.
    4. Auto-Complete: Scrub to 90% (1620s / 1800s), verify completed_at is set in backend DB.
    5. Time-Windowed Live Session: Verify 403 outside UTC window and 200 inside UTC window.
    """
    print("\n" + "=" * 78)
    print("PHASE 4 TERMINAL VERIFICATION: CLASSROOM, VIDEO & TIME-WINDOWED LIVE LECTURES")
    print("=" * 78)

    course = Course.objects.create(
        title="Diploma in Clinical & Applied Psychology",
        slug="diploma-phase4-terminal-check",
        level=Course.Level.DIPLOMA,
        residency=Course.Residency.OPTIONAL,
        status=Course.Status.PUBLISHED,
    )
    Price.objects.create(
        course=course,
        audience=Price.Audience.LOCAL,
        currency=Price.Currency.KES,
        amount_minor=18_000_000,
    )
    cohort = Cohort.objects.create(
        course=course,
        name="February 2027 Intake",
        starts_on=date(2027, 2, 1),
        capacity=25,
        enrollment_open=True,
    )
    module = Module.objects.create(
        course=course,
        order=1,
        title="Module 1: Clinical Interviewing & Formulation",
    )
    video_lesson = Lesson.objects.create(
        module=module,
        order=1,
        title="Therapeutic Boundaries & Informed Consent",
        kind=Lesson.Kind.VIDEO,
        duration_seconds=1800,
        video_asset_id="PRIVATE_MANAGED_VIDEO_ASSET_001",
        reading_body="Dr. Violet's lecture notes on clinical boundaries.",
        is_published=True,
    )

    now_utc = timezone.now()
    locked_live_session = LiveSession.objects.create(
        cohort=cohort,
        title="Future Live Lecture (3 Hours Away - Outside UTC Window)",
        starts_at=now_utc + timedelta(hours=3),
        duration_minutes=90,
        meet_url="https://meet.google.com/locked-future-lecture",
    )
    open_live_session = LiveSession.objects.create(
        cohort=cohort,
        title="Active Live Lecture (Starts in 10 Mins - Inside UTC Window)",
        starts_at=now_utc + timedelta(minutes=10),
        duration_minutes=90,
        meet_url="https://meet.google.com/open-live-lecture",
    )

    dr_violet = User.objects.create_superuser(
        email="dr.violet@edenlms.org",
        password="AdminPassword!2026",
    )
    student = User.objects.create_user(
        email="precious.student@edenlms.org",
        password="StudentPassword!2026",
    )
    Profile.objects.create(
        user=student,
        display_name="Precious M.",
        country="KE",
        timezone="Africa/Nairobi",
    )

    enrollment = Enrollment.objects.create(
        user=student,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )

    client = APIClient()
    client.force_authenticate(user=student)
    classroom_url = reverse("classroom:course-classroom", kwargs={"slug": course.slug})

    # 1. Verify blocked before Admin marks as paid
    blocked_res = client.get(classroom_url)
    assert blocked_res.status_code == 403
    print(f"[1/5] Unpaid Enrollment Gate: HTTP {blocked_res.status_code} (Blocked before admin activation)")

    # Execute Django Admin "Mark as Paid Manually" action as Dr. Violet
    factory = RequestFactory()
    admin_req = factory.post("/admin/enrollments/enrollment/")
    admin_req.user = dr_violet
    admin_req.session = "session"
    admin_req._messages = FallbackStorage(admin_req)
    modeladmin = EnrollmentAdmin(Enrollment, AdminSite())
    mark_enrollments_active_manually(
        modeladmin,
        admin_req,
        Enrollment.objects.filter(pk=enrollment.pk),
    )

    enrollment.refresh_from_db()
    assert enrollment.status == Enrollment.Status.ACTIVE
    print(
        f"      Admin Action Executed -> Enrollment Status: '{enrollment.status}' "
        f"(Source: {enrollment.activation_source})"
    )

    # 2. Video Watermark Verification
    token_url = reverse(
        "classroom:lesson-playback-token",
        kwargs={"lesson_id": video_lesson.id},
    )
    token_res = client.post(token_url)
    assert token_res.status_code == 200
    token_payload = token_res.json()

    encoded_claims = token_payload["playback_token"].split(".")[0]
    padded = encoded_claims + "=" * (-len(encoded_claims) % 4)
    decoded_claims = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))

    assert token_payload["watermark_email"] == "precious.student@edenlms.org"
    assert decoded_claims["watermark"] == "precious.student@edenlms.org"
    print(
        f"[2/5] Video Watermark Verified: Overlay Email = '{token_payload['watermark_email']}' "
        f"| Signed Token Claim = '{decoded_claims['watermark']}'"
    )

    # 3. Resume Playback (Play for 15 seconds, refresh page, verify last_position_s == 15)
    progress_url = reverse(
        "classroom:lesson-progress",
        kwargs={"lesson_id": video_lesson.id},
    )
    play_15s_res = client.post(progress_url, {"last_position_s": 15}, format="json")
    assert play_15s_res.status_code == 200

    refresh_res = client.get(classroom_url)
    assert refresh_res.status_code == 200
    refreshed_lesson = refresh_res.json()["modules"][0]["lessons"][0]
    assert refreshed_lesson["progress"]["last_position_s"] == 15
    assert refreshed_lesson["progress"]["status"] == LessonProgress.Status.IN_PROGRESS
    print(
        f"[3/5] Resume Playback Verified: Played 15s -> Page Refreshed -> "
        f"Resumed at last_position_s={refreshed_lesson['progress']['last_position_s']}s "
        f"(status='{refreshed_lesson['progress']['status']}')"
    )

    # 4. Auto-Complete (Scrub to 90% = 1620s of 1800s video -> triggers completed_at in DB)
    ninety_pct_seconds = int(video_lesson.duration_seconds * 0.9)
    scrub_res = client.post(
        progress_url,
        {"last_position_s": ninety_pct_seconds},
        format="json",
    )
    assert scrub_res.status_code == 200
    db_progress = LessonProgress.objects.get(user=student, lesson=video_lesson)
    assert db_progress.status == LessonProgress.Status.COMPLETED
    assert db_progress.completed_at is not None
    print(
        f"[4/5] 90% Scrub Auto-Complete Verified: Scrubbed to {ninety_pct_seconds}s/1800s (90%) -> "
        f"DB status='{db_progress.status}', completed_at={db_progress.completed_at.isoformat()}"
    )

    # 5. Time-Windowed Live Session (Outside UTC window -> hidden/403; Inside window -> 200)
    sessions_in_overview = {
        s["id"]: s for s in refresh_res.json()["live_sessions"]
    }
    assert sessions_in_overview[str(locked_live_session.id)]["join_window_open"] is False
    assert sessions_in_overview[str(open_live_session.id)]["join_window_open"] is True

    outside_join_res = client.get(
        reverse(
            "classroom:live-session-join",
            kwargs={"session_id": locked_live_session.id},
        )
    )
    assert outside_join_res.status_code == 403

    inside_join_res = client.get(
        reverse(
            "classroom:live-session-join",
            kwargs={"session_id": open_live_session.id},
        )
    )
    assert inside_join_res.status_code == 200
    assert inside_join_res.json()["meet_url"] == "https://meet.google.com/open-live-lecture"
    print(
        f"[5/5] Time-Windowed Live Lecture Verified: Outside UTC Window -> "
        f"join_window_open=False & HTTP {outside_join_res.status_code} | "
        f"Inside UTC Window -> HTTP {inside_join_res.status_code} ({inside_join_res.json()['meet_url']})"
    )


@pytest.mark.django_db(transaction=True)
def test_phase_5_residency_booking_and_simultaneous_two_browser_last_seat_race():
    """
    End-to-end terminal verification for Phase 5:
    1. Book an Embu 5-day residency block ($100 USD covering lunch & teas).
    2. Simulate 2 separate browser sessions clicking 'Book' at the exact same instant
       (via threading.Barrier) for the last available seat (capacity=1) in a Nairobi block.
       Prove select_for_update() + atomic seat constraint allows 1 to succeed (HTTP 201)
       and 1 to fail gracefully (HTTP 400).
    """
    print("\n" + "=" * 78)
    print("PHASE 5 TERMINAL VERIFICATION: RESIDENCY BOOKING & 2-BROWSER CONCURRENCY RACE")
    print("=" * 78)

    course = Course.objects.create(
        title="Certificate in Counselling Psychology",
        slug="cert-phase5-concurrency-check",
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

    embu_block = ResidencyBlock.objects.create(
        course=course,
        location=ResidencyBlock.Location.EMBU,
        title="Embu 5-Day Practical Block",
        starts_on=date(2027, 4, 5),
        ends_on=date(2027, 4, 9),
        capacity=15,
        fee_minor=10_000,
        currency=Price.Currency.USD,
        is_open=True,
    )

    nairobi_last_seat_block = ResidencyBlock.objects.create(
        course=course,
        location=ResidencyBlock.Location.NAIROBI,
        title="Nairobi 5-Day Practical Block (Last Seat Available)",
        starts_on=date(2027, 4, 12),
        ends_on=date(2027, 4, 16),
        capacity=1,
        fee_minor=10_000,
        currency=Price.Currency.USD,
        is_open=True,
    )

    student_a = User.objects.create_user(
        email="browser.a@edenlms.org",
        password="BrowserAPassword!2026",
    )
    Profile.objects.create(user=student_a, display_name="Browser A Student", country="KE")
    Enrollment.objects.create(
        user=student_a,
        cohort=cohort,
        status=Enrollment.Status.ACTIVE,
    )

    student_b = User.objects.create_user(
        email="browser.b@edenlms.org",
        password="BrowserBPassword!2026",
    )
    Profile.objects.create(user=student_b, display_name="Browser B Student", country="KE")
    Enrollment.objects.create(
        user=student_b,
        cohort=cohort,
        status=Enrollment.Status.ACTIVE,
    )

    client_a = APIClient()
    client_a.force_authenticate(user=student_a)
    booking_url = reverse("residency:registration-list-create")

    embu_res = client_a.post(
        booking_url,
        {
            "block_id": str(embu_block.id),
            "dietary_notes": "No dairy, herbal tea",
        },
        format="json",
    )
    assert embu_res.status_code == 201
    embu_data = embu_res.json()
    assert embu_data["seat_number"] == 1
    assert embu_data["payment"]["amount_minor"] == 10_000
    assert embu_data["payment"]["currency"] == "USD"
    print(
        f"[1/2] Embu Residency Booking Verified: HTTP {embu_res.status_code} -> "
        f"Seat #{embu_data['seat_number']} | Fee: {embu_data['payment']['currency']} "
        f"{embu_data['payment']['amount_major']} (Lunch & Teas Notice Attached)"
    )

    sync_barrier = threading.Barrier(2)

    def simulate_browser_booking(user, browser_label: str) -> dict:
        close_old_connections()
        try:
            browser_client = APIClient()
            browser_client.force_authenticate(user=user)
            sync_barrier.wait(timeout=5)
            response = browser_client.post(
                booking_url,
                {
                    "block_id": str(nairobi_last_seat_block.id),
                    "dietary_notes": f"Booked from {browser_label}",
                },
                format="json",
            )
            return {
                "browser": browser_label,
                "status_code": response.status_code,
                "body": response.json(),
            }
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(simulate_browser_booking, student_a, "Browser-1 (Chrome)"),
            pool.submit(simulate_browser_booking, student_b, "Browser-2 (Firefox)"),
        ]
        results = [f.result() for f in futures]

    status_codes = sorted(r["status_code"] for r in results)
    assert status_codes == [201, 400]

    winner = next(r for r in results if r["status_code"] == 201)
    loser = next(r for r in results if r["status_code"] == 400)

    assert ResidencyRegistration.objects.filter(block=nairobi_last_seat_block).count() == 1
    print(
        f"[2/2] Simultaneous 2-Browser Last-Seat Race Verified (select_for_update):\n"
        f"      -> WINNER: {winner['browser']} received HTTP {winner['status_code']} "
        f"(Allocated Seat #{winner['body']['seat_number']})\n"
        f"      -> GRACEFUL FAIL: {loser['browser']} received HTTP {loser['status_code']} "
        f"('{loser['body']['detail']}')"
    )
    print("=" * 78 + "\n")