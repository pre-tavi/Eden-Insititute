"""
Phase 3 Payment & Security Test Suite for Dr. Violet's LMS (EdenLMS).
Verifies:
1. Server-side audience pricing authority (local KES vs international USD).
2. DPO payment initiation and server-to-server verification (`verify_and_activate_dpo_payment`).
3. Idempotent handling of duplicate notifications / return callbacks (`UNIQUE(provider, provider_ref)`).
4. Strict rejection of tampered amounts or currencies (`status = TAMPERED`).
5. Rejection of client-supplied price or status overrides.
"""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.catalog.models import Cohort, Course, Price
from apps.enrollments.models import Enrollment
from apps.payments.models import Payment
from apps.payments.services import (
    DpoVerificationResult,
    initiate_enrollment_payment,
    verify_and_activate_dpo_payment,
)

User = get_user_model()


@pytest.fixture
def payment_setup():
    """Create a published Certificate course with local KES and international USD prices, and an open cohort."""
    course = Course.objects.create(
        title="Certificate in Counselling Psychology",
        slug="cert-counselling-payment-test",
        summary="Weekly live lectures plus optional 5-day practical block in Nairobi or Embu.",
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
    cohort = Cohort.objects.create(
        course=course,
        name="January 2027 Intake",
        starts_on=date(2027, 1, 15),
        capacity=30,
        enrollment_open=True,
    )

    # Local student (Kenya)
    student_ke = User.objects.create_user(
        email="amina.ke@example.com",
        password="SecurePassword!2026",
    )
    Profile.objects.create(
        user=student_ke,
        display_name="Amina Wanjiku",
        country="KE",
        timezone="Africa/Nairobi",
    )

    # International student (UK)
    student_uk = User.objects.create_user(
        email="oliver.uk@example.com",
        password="SecurePassword!2026",
    )
    Profile.objects.create(
        user=student_uk,
        display_name="Oliver Smith",
        country="GB",
        timezone="Europe/London",
    )

    return {
        "cohort": cohort,
        "student_ke": student_ke,
        "student_uk": student_uk,
    }


@pytest.mark.django_db
def test_server_audience_pricing_and_payment_initiation(payment_setup):
    """Verify that local students are priced in KES and international students in USD on the server."""
    cohort = payment_setup["cohort"]
    student_ke = payment_setup["student_ke"]
    student_uk = payment_setup["student_uk"]

    # 1. Local student enrollment & DPO payment initiation
    enroll_ke = Enrollment.objects.create(
        user=student_ke,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )
    payment_ke = initiate_enrollment_payment(
        enrollment=enroll_ke,
        redirect_url="http://localhost:5173/my-learning?dpo_return=1",
        back_url="http://localhost:5173/my-learning",
    )
    assert payment_ke.currency == "KES"
    assert payment_ke.amount_minor == 3_500_000
    assert payment_ke.status == Payment.Status.INITIATED
    assert payment_ke.provider_ref.startswith("DPO-SANDBOX-")

    # 2. International student enrollment & DPO payment initiation
    enroll_uk = Enrollment.objects.create(
        user=student_uk,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )
    payment_uk = initiate_enrollment_payment(
        enrollment=enroll_uk,
        redirect_url="http://localhost:5173/my-learning?dpo_return=1",
        back_url="http://localhost:5173/my-learning",
    )
    assert payment_uk.currency == "USD"
    assert payment_uk.amount_minor == 55_000
    assert payment_uk.status == Payment.Status.INITIATED


@pytest.mark.django_db
def test_server_to_server_verification_and_idempotency(payment_setup):
    """
    Verify that:
    - verify_and_activate_dpo_payment() verifies the transaction and sets Enrollment status to ACTIVE.
    - Subsequent duplicate notifications are handled idempotently without re-triggering activation.
    """
    cohort = payment_setup["cohort"]
    student_ke = payment_setup["student_ke"]

    enrollment = Enrollment.objects.create(
        user=student_ke,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )
    payment = initiate_enrollment_payment(
        enrollment=enrollment,
        redirect_url="http://localhost:5173/my-learning?dpo_return=1",
        back_url="http://localhost:5173/my-learning",
    )

    # First verification callback (e.g. DPO webhook)
    verified = verify_and_activate_dpo_payment(
        provider_ref=payment.provider_ref,
        trigger_source="test_webhook_1",
    )
    assert verified.status == Payment.Status.VERIFIED
    enrollment.refresh_from_db()
    assert enrollment.status == Enrollment.Status.ACTIVE
    assert enrollment.activation_source.startswith("dpo_verified:")

    # Second duplicate verification callback (Idempotency test)
    verified_again = verify_and_activate_dpo_payment(
        provider_ref=payment.provider_ref,
        trigger_source="test_webhook_duplicate",
    )
    assert verified_again.status == Payment.Status.VERIFIED
    # Check that raw_log recorded the idempotent duplicate note
    verifications = verified_again.raw_log.get("verifications", [])
    notes = [v.get("note") for v in verifications if v.get("note")]
    assert any("Idempotent duplicate notification ignored" in n for n in notes)


@pytest.mark.django_db
def test_tampered_amount_or_currency_is_rejected(payment_setup):
    """Pre-Deployment Security Checklist #22: Rejection of tampered payment amounts or currencies."""
    cohort = payment_setup["cohort"]
    student_ke = payment_setup["student_ke"]

    enrollment = Enrollment.objects.create(
        user=student_ke,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )
    payment = initiate_enrollment_payment(
        enrollment=enrollment,
        redirect_url="http://localhost:5173/my-learning?dpo_return=1",
        back_url="http://localhost:5173/my-learning",
    )

    # Simulate DPO returning a tampered/fraudulent amount (e.g. 1.00 KES instead of 35000.00 KES)
    tampered_override = DpoVerificationResult(
        result_code="000",
        result_explanation="Transaction Paid",
        transaction_amount_minor=100,  # KES 1.00 (tampered!)
        transaction_currency="KES",
        customer_credit_type="CARD",
        raw_xml="<API3G><Result>000</Result><TransactionAmount>1.00</TransactionAmount></API3G>",
    )

    with pytest.raises(ValidationError, match="Payment integrity violation"):
        verify_and_activate_dpo_payment(
            provider_ref=payment.provider_ref,
            verification_override=tampered_override,
            trigger_source="tampered_test",
        )

    payment.refresh_from_db()
    assert payment.status == Payment.Status.TAMPERED
    enrollment.refresh_from_db()
    assert enrollment.status == Enrollment.Status.PENDING_PAYMENT


@pytest.mark.django_db
def test_api_payment_initiate_blocks_client_price_tampering(payment_setup):
    """Pre-Deployment Security Checklist #8 & #22: API rejects client-supplied price override fields."""
    student_ke = payment_setup["student_ke"]
    cohort = payment_setup["cohort"]

    enrollment = Enrollment.objects.create(
        user=student_ke,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )

    client = APIClient()
    client.force_authenticate(user=student_ke)

    # Attempt to inject amount/price in JSON body
    response = client.post(
        reverse("payments:payment-initiate"),
        {
            "enrollment_id": str(enrollment.id),
            "amount_minor": 100,
            "currency": "KES",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "Client-supplied price or status fields" in response.json()["detail"]