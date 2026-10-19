"""
Final Bug-Hunting Terminal Verification Suite for Dr. Violet's LMS (EdenLMS).
Targets:
1. Timezone Mismatch (UTC storage -> Africa/Nairobi EAT display + exact-second join window unlock).
2. Payment Webhook Idempotency (double POST replay to /api/payments/webhook/dpo/ + UNIQUE constraint).
3. Tampered Amounts (35,000 KES altered to 1 KES in checkout initiation and in DPO webhook verification).
4. Empty States (Student with 0 enrollments + Admin viewing django-axes with 0 access failures).

Run with: cd backend && pytest -s -v tests/test_bug_hunting_suite.py
"""
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from axes.models import AccessAttempt, AccessLog
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.catalog.models import Cohort, Course, Price
from apps.classroom.models import LiveSession
from apps.enrollments.models import Enrollment
from apps.payments.models import Payment
from apps.payments.services import (
    DpoVerificationResult,
    initiate_enrollment_payment,
)

User = get_user_model()


@pytest.fixture
def bug_hunt_setup():
    course = Course.objects.create(
        title="Certificate in Counselling Psychology",
        slug="cert-counselling-bughunt",
        summary="Weekly live lectures and optional 5-day practical block.",
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

    student = User.objects.create_user(
        email="nairobi.student@edenlms.org",
        password="StudentPassword!2026",
    )
    Profile.objects.create(
        user=student,
        display_name="Nairobi Student",
        country="KE",
        timezone="Africa/Nairobi",
    )

    return {
        "course": course,
        "cohort": cohort,
        "student": student,
    }


@pytest.mark.django_db
def test_1_timezone_mismatch_and_exact_second_live_session_unlock(bug_hunt_setup):
    print("\n" + "=" * 78)
    print("BUG HUNT #1: TIMEZONE MISMATCH (UTC -> AFRICA/NAIROBI) & EXACT-SECOND UNLOCK")
    print("=" * 78)

    cohort = bug_hunt_setup["cohort"]
    student = bug_hunt_setup["student"]
    Enrollment.objects.create(
        user=student,
        cohort=cohort,
        status=Enrollment.Status.ACTIVE,
    )

    starts_at_utc = datetime(2027, 1, 20, 12, 0, 0, tzinfo=UTC)
    live_session = LiveSession.objects.create(
        cohort=cohort,
        title="Trauma-Informed Intake Seminar",
        starts_at=starts_at_utc,
        duration_minutes=90,
        meet_url="https://meet.google.com/nairobi-eat-check",
    )

    nairobi_tz = ZoneInfo(student.profile.timezone)
    nairobi_local_dt = live_session.starts_at.astimezone(nairobi_tz)
    assert nairobi_local_dt.hour == 15
    assert nairobi_local_dt.minute == 0
    assert nairobi_local_dt.tzname() == "EAT"
    print(
        f"[PASS] Stored in DB (UTC):      {live_session.starts_at.isoformat()}\n"
        f"[PASS] Student Display (EAT):   {nairobi_local_dt.isoformat()} ({nairobi_local_dt.tzname()})"
    )

    client = APIClient()
    client.force_authenticate(user=student)
    join_url = reverse(
        "classroom:live-session-join",
        kwargs={"session_id": live_session.id},
    )

    one_second_early = starts_at_utc - timedelta(minutes=30, seconds=1)
    with patch("apps.classroom.models.timezone.now", return_value=one_second_early):
        res_early = client.get(join_url)
        assert res_early.status_code == 403
        print(
            f"[PASS] T-30m01s ({one_second_early.strftime('%H:%M:%S')} UTC): "
            f"HTTP {res_early.status_code} (Locked 1 second before window)"
        )

    exact_unlock_second = starts_at_utc - timedelta(minutes=30)
    with patch("apps.classroom.models.timezone.now", return_value=exact_unlock_second):
        res_exact = client.get(join_url)
        assert res_exact.status_code == 200
        assert res_exact.json()["meet_url"] == "https://meet.google.com/nairobi-eat-check"
        print(
            f"[PASS] T-30m00s ({exact_unlock_second.strftime('%H:%M:%S')} UTC): "
            f"HTTP {res_exact.status_code} -> Unlocked {res_exact.json()['meet_url']}"
        )


@pytest.mark.django_db
def test_2_payment_webhook_replay_idempotency_and_unique_constraint(bug_hunt_setup):
    print("\n" + "=" * 78)
    print("BUG HUNT #2: DPO WEBHOOK REPLAY IDEMPOTENCY & UNIQUE(provider, provider_ref)")
    print("=" * 78)

    cohort = bug_hunt_setup["cohort"]
    student = bug_hunt_setup["student"]
    enrollment = Enrollment.objects.create(
        user=student,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )

    payment = initiate_enrollment_payment(
        enrollment=enrollment,
        redirect_url="http://localhost:5173/my-learning?dpo_return=1",
        back_url="http://localhost:5173/my-learning",
    )

    webhook_client = APIClient()
    webhook_url = reverse("payments:dpo-webhook")
    
    # BUG 2 FIX: Changed raw XML text to JSON payload, as the view expects JSON
    webhook_payload = {"TransToken": payment.provider_ref}

    res_1 = webhook_client.post(
        webhook_url,
        data=webhook_payload,
        format="json",
    )
    assert res_1.status_code == 200
    enrollment.refresh_from_db()
    first_activated_at = enrollment.activated_at
    assert enrollment.status == Enrollment.Status.ACTIVE
    assert first_activated_at is not None

    res_2 = webhook_client.post(
        webhook_url,
        data=webhook_payload,
        format="json",
    )
    assert res_2.status_code == 200
    enrollment.refresh_from_db()
    payment.refresh_from_db()

    assert enrollment.status == Enrollment.Status.ACTIVE
    assert enrollment.activated_at == first_activated_at
    assert len(payment.raw_log["verifications"]) == 2
    assert "Idempotent duplicate notification ignored" in payment.raw_log["verifications"][1]["note"]
    print(
        f"[PASS] Webhook Call #1 -> HTTP {res_1.status_code} (Activated at {first_activated_at.isoformat()})\n"
        f"[PASS] Webhook Replay #2 -> HTTP {res_2.status_code} (No crash, activated_at unchanged, logged as duplicate)"
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Payment.objects.create(
            enrollment=enrollment,
            provider=Payment.Provider.DPO,
            provider_ref=payment.provider_ref,
            company_ref="EDEN-DUPLICATE-TEST",
            amount_minor=3_500_000,
            currency="KES",
        )
    print(
        f"[PASS] UNIQUE(provider, provider_ref) Constraint Verified: "
        f"Duplicate ref '{payment.provider_ref}' rejected with IntegrityError"
    )


@pytest.mark.django_db
def test_3_tampered_amounts_in_devtools_and_webhook_verification(bug_hunt_setup):
    print("\n" + "=" * 78)
    print("BUG HUNT #3: TAMPERED AMOUNTS (35,000 KES -> 1 KES INTERCEPTION TEST)")
    print("=" * 78)

    cohort = bug_hunt_setup["cohort"]
    student = bug_hunt_setup["student"]
    enrollment = Enrollment.objects.create(
        user=student,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )

    client = APIClient()
    client.force_authenticate(user=student)
    initiate_url = reverse("payments:payment-initiate")

    devtools_tamper_res = client.post(
        initiate_url,
        {
            "enrollment_id": str(enrollment.id),
            "amount": 1,
            "amount_minor": 100,
        },
        format="json",
    )
    assert devtools_tamper_res.status_code == 400
    print(
        f"[PASS] Stage A (DevTools Request Tamper: amount=1): "
        f"HTTP {devtools_tamper_res.status_code} -> '{devtools_tamper_res.json()['detail']}'"
    )

    legit_init_res = client.post(
        initiate_url,
        {"enrollment_id": str(enrollment.id)},
        format="json",
    )
    assert legit_init_res.status_code == 201
    provider_ref = legit_init_res.json()["provider_ref"]
    assert legit_init_res.json()["amount_minor"] == 3_500_000

    tampered_dpo_response = DpoVerificationResult(
        result_code="000",
        result_explanation="Transaction Paid",
        transaction_amount_minor=100,
        transaction_currency="KES",
        customer_credit_type="M-PESA",
        raw_xml="<API3G><Result>000</Result><TransactionAmount>1.00</TransactionAmount><TransactionCurrency>KES</TransactionCurrency></API3G>",
    )

    webhook_client = APIClient()
    with patch(
        "apps.payments.services.fetch_dpo_verification_from_provider",
        return_value=tampered_dpo_response,
    ):
        webhook_res = webhook_client.post(
            reverse("payments:dpo-webhook"),
            {"TransToken": provider_ref},
            format="json",
        )

    assert webhook_res.status_code == 400
    payment = Payment.objects.get(provider_ref=provider_ref)
    enrollment.refresh_from_db()

    assert payment.status == Payment.Status.TAMPERED
    assert enrollment.status == Enrollment.Status.PENDING_PAYMENT
    print(
        f"[PASS] Stage B (Webhook Verification Tamper: 35,000 KES -> 1 KES): "
        f"HTTP {webhook_res.status_code} | Payment.status='{payment.status}' | "
        f"Enrollment.status='{enrollment.status}'"
    )


@pytest.mark.django_db
def test_4_empty_states_for_new_student_and_admin_access_failures(bug_hunt_setup):
    print("\n" + "=" * 78)
    print("BUG HUNT #4: EMPTY STATES (0 ENROLLMENTS STUDENT & 0 ACCESS FAILURES ADMIN)")
    print("=" * 78)

    student = bug_hunt_setup["student"]
    student_client = APIClient()
    student_client.force_authenticate(user=student)

    enroll_res = student_client.get(reverse("enrollments:enrollment-list-create"))
    assert enroll_res.status_code == 200
    assert enroll_res.json() == {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }

    residency_res = student_client.get(reverse("residency:registration-list-create"))
    assert residency_res.status_code == 200
    assert residency_res.json() == []
    print(
        f"[PASS] Student Empty State: GET /api/enrollments/ -> HTTP {enroll_res.status_code} "
        f"(count=0, results=[]) | GET /api/residency/registrations/ -> []"
    )

    AccessAttempt.objects.all().delete()
    AccessLog.objects.all().delete()
    assert AccessAttempt.objects.count() == 0

    dr_violet = User.objects.create_superuser(
        email="admin.emptycheck@edenlms.org",
        password="AdminPassword!2026",
    )
    admin_client = APIClient()
    admin_client.force_login(dr_violet)

    axes_attempt_url = reverse("admin:axes_accessattempt_changelist")
    axes_attempt_res = admin_client.get(axes_attempt_url)
    assert axes_attempt_res.status_code == 200
    axes_html = axes_attempt_res.content.decode("utf-8")
    assert "0 access attempts" in axes_html.lower()
    print(
        f"[PASS] Admin Empty State: GET {axes_attempt_url} -> HTTP {axes_attempt_res.status_code} "
        f"('0 access attempts' rendered cleanly in Django Admin)"
    )
    print("=" * 78 + "\n")