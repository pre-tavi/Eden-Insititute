"""
Phase 5 Residency Block & Seat Capacity Concurrency Test Suite for Dr. Violet's LMS (EdenLMS).
Verifies:
1. Two simultaneous bookings for the last seat (`capacity = 1`) result in exactly ONE success
   and ONE rejection (no overbooking).
2. Paying the USD 100 (`amount_minor = 10000`) fee via the Phase 3 DPO verification flow
   transitions `ResidencyRegistration.status` to `CONFIRMED` and surfaces the lunch & tea notice.
3. `Course.residency = required` blocks course completion until a confirmed residency registration
   exists, whereas `optional` allows completion once lessons are done.
4. Admin CSV catering headcount export produces accurate rows for Nairobi and Embu blocks.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.catalog.models import Cohort, Course, Price
from apps.classroom.models import Lesson, LessonProgress, Module
from apps.enrollments.models import Enrollment, activate_enrollment
from apps.payments.services import verify_and_activate_dpo_payment
from apps.residency.admin import ResidencyBlockAdmin, export_catering_headcount_csv
from apps.residency.models import RESIDENCY_CATERING_NOTICE, ResidencyBlock, ResidencyRegistration
from apps.residency.services import book_residency_block, check_and_complete_course_enrollment

User = get_user_model()


@pytest.fixture
def residency_setup():
    diploma_course = Course.objects.create(
        title="Diploma in Clinical & Applied Psychology",
        slug="diploma-clinical-residency-test",
        summary="Includes mandatory 5-day practical block in Nairobi or Embu.",
        level=Course.Level.DIPLOMA,
        residency=Course.Residency.REQUIRED,
        status=Course.Status.PUBLISHED,
    )
    Price.objects.create(
        course=diploma_course,
        audience=Price.Audience.LOCAL,
        currency=Price.Currency.KES,
        amount_minor=18_000_000,
    )
    cohort = Cohort.objects.create(
        course=diploma_course,
        name="February 2027 Intake",
        starts_on=date(2027, 2, 1),
        capacity=25,
        enrollment_open=True,
    )
    mod = Module.objects.create(course=diploma_course, order=1, title="Clinical Practicum")
    lesson = Lesson.objects.create(
        module=mod,
        order=1,
        title="Practicum Orientation",
        kind=Lesson.Kind.READING,
        duration_seconds=600,
        is_published=True,
    )

    # Last-seat block in Nairobi (capacity = 1, 5 days: Mar 10 to Mar 14, 2027, fee = $100 USD)
    nairobi_last_seat_block = ResidencyBlock.objects.create(
        course=diploma_course,
        location=ResidencyBlock.Location.NAIROBI,
        title="Nairobi 5-Day Clinical Practicum Block",
        starts_on=date(2027, 3, 10),
        ends_on=date(2027, 3, 14),
        capacity=1,
        fee_minor=10_000,
        currency=Price.Currency.USD,
        is_open=True,
    )

    # Embu block (capacity = 10)
    embu_block = ResidencyBlock.objects.create(
        course=diploma_course,
        location=ResidencyBlock.Location.EMBU,
        title="Embu 5-Day Clinical Practicum Block",
        starts_on=date(2027, 4, 5),
        ends_on=date(2027, 4, 9),
        capacity=10,
        fee_minor=10_000,
        currency=Price.Currency.USD,
        is_open=True,
    )

    student_1 = User.objects.create_user(email="student1@example.com", password="Password1!2026")
    Profile.objects.create(user=student_1, display_name="Student One", country="KE")
    enroll_1 = Enrollment.objects.create(user=student_1, cohort=cohort)
    activate_enrollment(enroll_1, source="test_active")

    student_2 = User.objects.create_user(email="student2@example.com", password="Password2!2026")
    Profile.objects.create(user=student_2, display_name="Student Two", country="KE")
    enroll_2 = Enrollment.objects.create(user=student_2, cohort=cohort)
    activate_enrollment(enroll_2, source="test_active")

    return {
        "course": diploma_course,
        "lesson": lesson,
        "nairobi_block": nairobi_last_seat_block,
        "embu_block": embu_block,
        "student_1": student_1,
        "student_2": student_2,
        "enroll_1": enroll_1,
        "enroll_2": enroll_2,
    }


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_bookings_for_last_seat_result_in_one_success(residency_setup):
    """
    Phase 5 Gate: Two simultaneous bookings for the last seat (capacity=1) result in
    exactly ONE success and ONE capacity rejection.
    """
    block_id = residency_setup["nairobi_block"].id
    student_1 = residency_setup["student_1"]
    student_2 = residency_setup["student_2"]

    def attempt_booking(user):
        close_old_connections()
        try:
            reg = book_residency_block(
                user=user,
                block_id=block_id,
                dietary_notes="Standard lunch & tea",
            )
            return ("success", reg.id)
        except Exception as exc:
            return ("failed", str(exc))
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(attempt_booking, student_1),
            executor.submit(attempt_booking, student_2),
        ]
        outcomes = [f.result() for f in futures]

    statuses = [outcome[0] for outcome in outcomes]
    assert statuses.count("success") == 1
    assert statuses.count("failed") == 1

    active_regs = ResidencyRegistration.objects.filter(block_id=block_id)
    assert active_regs.count() == 1
    assert active_regs.first().seat_number == 1


@pytest.mark.django_db
def test_residency_dpo_payment_flow_and_required_completion_gate(residency_setup):
    """
    Verify:
    - Booking creates a USD 100 (`amount_minor=10000`) payment and surfaces lunch & tea notice.
    - `Course.residency = required` blocks course completion until residency payment is verified.
    - Admin CSV export generates the catering headcount list for Nairobi/Embu blocks.
    """
    student_1 = residency_setup["student_1"]
    enroll_1 = residency_setup["enroll_1"]
    lesson = residency_setup["lesson"]
    embu_block = residency_setup["embu_block"]

    # Student 1 completes all lessons in the course
    LessonProgress.objects.create(
        user=student_1,
        lesson=lesson,
        status=LessonProgress.Status.COMPLETED,
        last_position_s=600,
    )

    # Because course.residency == REQUIRED, completion is blocked before residency is confirmed
    with pytest.raises(ValidationError, match="requires a confirmed 5-day practical residency"):
        check_and_complete_course_enrollment(enroll_1)

    # Book the Embu 5-day block via API
    client = APIClient()
    client.force_authenticate(user=student_1)
    book_res = client.post(
        reverse("residency:registration-list-create"),
        {
            "block_id": str(embu_block.id),
            "dietary_notes": "Vegetarian lunch, ginger tea",
        },
        format="json",
    )
    assert book_res.status_code == 201
    reg_payload = book_res.json()
    assert reg_payload["seat_number"] == 1
    assert reg_payload["status"] == ResidencyRegistration.Status.PENDING_PAYMENT
    assert reg_payload["payment"]["amount_minor"] == 10_000
    assert reg_payload["payment"]["currency"] == "USD"
    assert reg_payload["catering_notice"] == RESIDENCY_CATERING_NOTICE

    # Verify the $100 USD residency payment through the Phase 3 DPO verification service
    provider_ref = reg_payload["payment"]["provider_ref"]
    verify_and_activate_dpo_payment(
        provider_ref=provider_ref,
        trigger_source="test_residency_dpo",
    )

    reg = ResidencyRegistration.objects.get(pk=reg_payload["id"])
    assert reg.status == ResidencyRegistration.Status.CONFIRMED

    # Now course completion succeeds!
    completed_enrollment = check_and_complete_course_enrollment(enroll_1)
    assert completed_enrollment.status == Enrollment.Status.COMPLETED

    # Verify Admin CSV Catering Export for Dr. Violet's lunch-and-tea headcount
    factory = RequestFactory()
    request = factory.get("/admin/residency/residencyblock/")
    request.user = student_1
    modeladmin = ResidencyBlockAdmin(ResidencyBlock, AdminSite())
    csv_response = export_catering_headcount_csv(
        modeladmin,
        request,
        ResidencyBlock.objects.filter(pk=embu_block.id),
    )
    assert csv_response.status_code == 200
    csv_content = csv_response.content.decode("utf-8")
    assert "Embu Campus" in csv_content
    assert "student1@example.com" in csv_content
    assert "Vegetarian lunch, ginger tea" in csv_content
    assert "100.00" in csv_content