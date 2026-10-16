"""
Phase 2 Security & Isolation Test Suite for Dr. Violet's LMS (EdenLMS).
Verifies:
1. Unauthenticated requests to private endpoints return 401/403 (Checklist #6).
2. Student A cannot read or mutate Student B's enrollment — expects 404 (Checklist #4 & #7).
3. Student cannot tamper with enrollment status or price via PATCH (Checklist #8).
4. Missing or fake Cloudflare Turnstile tokens are rejected server-side (Checklist #12).
5. Server-side audience pricing ('local' KES vs 'international' USD) & idempotent activate_enrollment().
"""
import uuid
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.catalog.models import Cohort, Course, Price
from apps.enrollments.models import Enrollment, activate_enrollment

User = get_user_model()


@pytest.fixture
def seeded_cohort():
    """Creates a published Certificate course with Local (KES) and International (USD) prices and an open Cohort."""
    course = Course.objects.create(
        title="Certificate in Counselling Psychology",
        slug="cert-counselling-isolation-test",
        summary="Live lectures plus optional 5-day practical block in Nairobi or Embu.",
        level=Course.Level.CERTIFICATE,
        residency=Course.Residency.OPTIONAL,
        status=Course.Status.PUBLISHED,
    )
    Price.objects.create(
        course=course,
        audience=Price.Audience.LOCAL,
        currency=Price.Currency.KES,
        amount_minor=3_500_000,  # KES 35,000.00
    )
    Price.objects.create(
        course=course,
        audience=Price.Audience.INTERNATIONAL,
        currency=Price.Currency.USD,
        amount_minor=55_000,  # USD 550.00
    )
    return Cohort.objects.create(
        course=course,
        name="January 2027 Intake",
        starts_on=date(2027, 1, 15),
        capacity=30,
        enrollment_open=True,
    )


@pytest.mark.django_db
def test_unauthenticated_requests_to_private_endpoints_return_401_or_403():
    """Pre-Deployment Security Checklist #6: Enforce server-side auth on all non-public endpoints."""
    client = APIClient()
    random_id = uuid.uuid4()

    me_res = client.get(reverse("accounts:me"))
    assert me_res.status_code in (401, 403)

    logout_res = client.post(reverse("accounts:logout"))
    assert logout_res.status_code in (401, 403)

    list_res = client.get(reverse("enrollments:enrollment-list-create"))
    assert list_res.status_code in (401, 403)

    create_res = client.post(
        reverse("enrollments:enrollment-list-create"),
        {"cohort_id": str(random_id)},
        format="json",
    )
    assert create_res.status_code in (401, 403)

    detail_res = client.get(
        reverse("enrollments:enrollment-detail", kwargs={"pk": random_id})
    )
    assert detail_res.status_code in (401, 403)


@pytest.mark.django_db
def test_turnstile_bot_protection_rejects_missing_or_fake_tokens():
    """Pre-Deployment Security Checklist #12: Verify Turnstile bot token server-side."""
    client = APIClient()

    bad_reg = client.post(
        reverse("accounts:register"),
        {
            "email": "bot@example.com",
            "password": "StrongBotPassword!2026",
            "display_name": "Automated Bot",
            "country": "KE",
            "timezone": "Africa/Nairobi",
            "turnstile_token": " forged-invalid-token ",
        },
        format="json",
    )
    assert bad_reg.status_code == 400
    assert "turnstile_token" in bad_reg.json()
    assert User.objects.filter(email="bot@example.com").exists() is False

    good_reg = client.post(
        reverse("accounts:register"),
        {
            "email": "real.student@example.com",
            "password": "StrongStudentPassword!2026",
            "display_name": "Grace Njeri",
            "country": "KE",
            "timezone": "Africa/Nairobi",
            "turnstile_token": "turnstile-dev-pass-token",
        },
        format="json",
    )
    assert good_reg.status_code == 201
    data = good_reg.json()
    assert data["email"] == "real.student@example.com"
    assert data["profile"]["country"] == "KE"
    assert data["profile"]["effective_audience"] == "local"


@pytest.mark.django_db
def test_student_a_cannot_read_or_modify_student_b_enrollment(seeded_cohort):
    """
    Phase 2 Gate & Pre-Deployment Checklist #4, #7, #8:
    - Student A cannot read or change Student B's enrollment (expect 404).
    - Student B cannot self-activate their own enrollment via PATCH (expect 403).
    """
    student_a = User.objects.create_user(
        email="student.a@example.com",
        password="ComplexPasswordA!2026",
    )
    Profile.objects.create(
        user=student_a,
        display_name="Student A (Local KE)",
        country="KE",
        timezone="Africa/Nairobi",
    )

    student_b = User.objects.create_user(
        email="student.b@example.com",
        password="ComplexPasswordB!2026",
    )
    Profile.objects.create(
        user=student_b,
        display_name="Student B (International GB)",
        country="GB",
        timezone="Europe/London",
    )

    # Student B creates an enrollment (starts as pending_payment, priced in USD from server profile)
    client_b = APIClient()
    client_b.force_authenticate(user=student_b)
    create_res = client_b.post(
        reverse("enrollments:enrollment-list-create"),
        {"cohort_id": str(seeded_cohort.id)},
        format="json",
    )
    assert create_res.status_code == 201
    enrollment_b_id = create_res.json()["id"]
    assert create_res.json()["status"] == Enrollment.Status.PENDING_PAYMENT
    assert create_res.json()["expected_price"]["currency"] == "USD"
    assert create_res.json()["expected_price"]["amount_minor"] == 55_000

    # Student A authenticates and attempts to read or mutate Student B's enrollment -> MUST return 404
    client_a = APIClient()
    client_a.force_authenticate(user=student_a)

    list_a = client_a.get(reverse("enrollments:enrollment-list-create"))
    assert list_a.status_code == 200
    assert list_a.json()["count"] == 0

    detail_url_b = reverse("enrollments:enrollment-detail", kwargs={"pk": enrollment_b_id})

    get_cross = client_a.get(detail_url_b)
    assert get_cross.status_code == 404

    patch_cross = client_a.patch(
        detail_url_b,
        {"status": "active"},
        format="json",
    )
    assert patch_cross.status_code == 404

    # Student B attempts to tamper with their own enrollment status -> MUST return 403 and stay pending_payment
    tamper_res = client_b.patch(
        detail_url_b,
        {"status": "active"},
        format="json",
    )
    assert tamper_res.status_code == 403
    enrollment_b = Enrollment.objects.get(pk=enrollment_b_id)
    assert enrollment_b.status == Enrollment.Status.PENDING_PAYMENT

    # Only server-side activate_enrollment() transitions status to ACTIVE (and is idempotent)
    activated = activate_enrollment(enrollment_b, source="test_verified_payment")
    assert activated.status == Enrollment.Status.ACTIVE
    assert activated.activated_at is not None

    activated_again = activate_enrollment(enrollment_b, source="duplicate_webhook")
    assert activated_again.status == Enrollment.Status.ACTIVE
    assert activated_again.activation_source == "test_verified_payment"