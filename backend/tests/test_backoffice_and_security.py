"""
Phase 6, Phase 7 & Phase 8 Back-Office, Staff 2FA, CSV Export, Backup Restore,
and Production Sandbox Lockout Test Suite.
"""
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, override_settings
from django_otp.admin import OTPAdminSite
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import Profile
from apps.accounts.turnstile import verify_turnstile_token
from apps.catalog.models import Cohort, Course, Price
from apps.classroom.models import Lesson, LessonProgress, Module
from apps.enrollments.admin import (
    EnrollmentAdmin,
    compute_enrollment_progress_percent,
    export_enrollments_progress_csv,
)
from apps.enrollments.models import Enrollment, activate_enrollment
from apps.payments.services import (
    PaymentIntegrationError,
    initiate_enrollment_payment,
)

User = get_user_model()


@pytest.mark.django_db
def test_instructor_backoffice_progress_percentage_and_csv_export():
    """Phase 6 Gate: Verify instructor admin student progress % and CSV export."""
    course = Course.objects.create(
        title="Certificate in Counselling Psychology",
        slug="cert-admin-progress-test",
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
        capacity=14,
        enrollment_open=True,
    )
    mod = Module.objects.create(course=course, order=1, title="Module 1")
    lesson_1 = Lesson.objects.create(
        module=mod,
        order=1,
        title="Lesson 1",
        kind=Lesson.Kind.VIDEO,
        duration_seconds=1200,
        is_published=True,
    )
    Lesson.objects.create(
        module=mod,
        order=2,
        title="Lesson 2",
        kind=Lesson.Kind.READING,
        duration_seconds=600,
        is_published=True,
    )

    student = User.objects.create_user(
        email="progress.student@example.com",
        password="StrongPassword!2026",
    )
    Profile.objects.create(
        user=student,
        display_name="Wanjiru Kamau",
        country="KE",
        timezone="Africa/Nairobi",
    )
    enrollment = Enrollment.objects.create(user=student, cohort=cohort)
    activate_enrollment(enrollment, source="dpo_verified:TEST")

    LessonProgress.objects.create(
        user=student,
        lesson=lesson_1,
        status=LessonProgress.Status.COMPLETED,
        last_position_s=1200,
    )

    assert compute_enrollment_progress_percent(enrollment) == 50

    modeladmin = EnrollmentAdmin(Enrollment, AdminSite())
    assert modeladmin.progress_percentage_display(enrollment) == "50%"

    factory = RequestFactory()
    request = factory.get("/admin/enrollments/enrollment/")
    request.user = student
    csv_res = export_enrollments_progress_csv(
        modeladmin,
        request,
        Enrollment.objects.filter(pk=enrollment.id),
    )
    assert csv_res.status_code == 200
    body = csv_res.content.decode("utf-8")
    assert "progress.student@example.com" in body
    assert "Wanjiru Kamau" in body
    assert "50%" in body


@pytest.mark.django_db
def test_staff_totp_2fa_device_and_otp_admin_site():
    """Phase 6 & Checklist #21: Verify django-otp TOTPDevice and OTPAdminSite 2FA enforcement."""
    dr_violet = User.objects.create_superuser(
        email="dr.violet@example.com",
        password="SuperSecureStaffPassword!2026",
    )
    device = TOTPDevice.objects.create(
        user=dr_violet,
        name="Dr. Violet Authenticator",
        confirmed=True,
    )
    assert device.confirmed is True

    otp_site = OTPAdminSite()
    assert otp_site.name == "otpadmin"

    factory = RequestFactory()
    request = factory.get("/admin/")
    dr_violet.is_verified = lambda: False
    request.user = dr_violet
    assert otp_site.has_permission(request) is False

    dr_violet.is_verified = lambda: True
    assert otp_site.has_permission(request) is True


def test_sqlite_backup_and_restore_integrity(tmp_path: Path):
    """Phase 7 & Checklist #24: Test automated database backup and restore round-trip."""
    source_db = tmp_path / "source.sqlite3"
    backup_db = tmp_path / "backup.sqlite3"

    conn_src = sqlite3.connect(source_db)
    conn_src.execute("CREATE TABLE audit_canary (id TEXT PRIMARY KEY, status TEXT)")
    conn_src.execute("INSERT INTO audit_canary VALUES ('eden-1', 'verified')")
    conn_src.commit()

    conn_bkp = sqlite3.connect(backup_db)
    with conn_bkp:
        conn_src.backup(conn_bkp)
    conn_bkp.close()
    conn_src.close()

    conn_verify = sqlite3.connect(backup_db)
    row = conn_verify.execute("SELECT id, status FROM audit_canary").fetchone()
    conn_verify.close()
    assert row == ("eden-1", "verified")


@pytest.mark.django_db
@override_settings(
    DEBUG=False,
    ALLOW_DEV_SANDBOX=False,
    DPO_COMPANY_TOKEN="sandbox-test-token",
)
def test_production_mode_rejects_dev_turnstile_and_dpo_sandbox():
    """Phase 8 Task 8.4: Verify dev Turnstile tokens and DPO sandbox tokens are blocked in production."""
    assert verify_turnstile_token("turnstile-dev-pass-token") is False

    course = Course.objects.create(
        title="Diploma in Counseling: Marriage and Family Therapy Option (KNEC)",
        slug="diploma-mft-prod-guard-test",
        level=Course.Level.DIPLOMA,
        residency=Course.Residency.REQUIRED,
        status=Course.Status.PUBLISHED,
    )
    Price.objects.create(
        course=course,
        audience=Price.Audience.LOCAL,
        currency=Price.Currency.KES,
        amount_minor=15_000_000,
    )
    cohort = Cohort.objects.create(
        course=course,
        name="January 2027 KNEC Intake",
        starts_on=date(2027, 1, 18),
        capacity=14,
        enrollment_open=True,
    )
    student = User.objects.create_user(
        email="prod.check@edenlms.org",
        password="StrongPassword!2026",
    )
    Profile.objects.create(user=student, display_name="Prod Check", country="KE")
    enrollment = Enrollment.objects.create(
        user=student,
        cohort=cohort,
        status=Enrollment.Status.PENDING_PAYMENT,
    )

    with pytest.raises(PaymentIntegrationError, match="disabled in production"):
        initiate_enrollment_payment(
            enrollment=enrollment,
            redirect_url="https://lms.edentherapy.co.ke/my-learning?dpo_return=1",
            back_url="https://lms.edentherapy.co.ke/my-learning",
        )