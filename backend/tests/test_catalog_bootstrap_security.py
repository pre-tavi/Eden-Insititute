"""Ensure catalog startup seeding cannot create or rewrite administrator credentials."""
from io import StringIO

import pytest
from axes.models import AccessAttempt
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from apps.accounts.models import Profile
from apps.catalog.models import Course

User = get_user_model()


@pytest.mark.django_db
def test_catalog_seed_does_not_create_default_administrator():
    call_command("seed_catalog", stdout=StringIO())

    assert not User.objects.filter(email="dr.violet@edenlms.org").exists()
    assert not StaticDevice.objects.exists()


@pytest.mark.django_db
def test_catalog_seed_does_not_provision_admin_or_clear_security_records():
    admin_email = "dr.violet@edenlms.org"
    admin = User.objects.create_superuser(
        email=admin_email,
        password="Existing-Admin-Password!2026",
    )
    original_password_hash = admin.password
    failed_attempt = AccessAttempt.objects.create(
        user_agent="pytest",
        ip_address="192.0.2.15",
        username=admin_email,
        http_accept="*/*",
        path_info="/eden-instructor-backoffice/login/",
        get_data="",
        post_data="",
        failures_since_start=3,
    )

    call_command("seed_catalog", stdout=StringIO())
    call_command("seed_catalog", stdout=StringIO())

    admin.refresh_from_db()
    assert admin.password == original_password_hash
    assert admin.check_password("Existing-Admin-Password!2026")
    assert AccessAttempt.objects.filter(pk=failed_attempt.pk).exists()
    assert not StaticDevice.objects.filter(user=admin).exists()
    assert not StaticToken.objects.filter(token="EDEN-2026-OTP").exists()
    assert Course.objects.filter(
        slug__in=(
            "diploma-counseling-marriage-family-therapy-knec",
            "certificate-counselling-psychology",
            "certificate-marriage-family-therapy-foundations",
        )
    ).count() == 3


@pytest.mark.django_db
def test_bootstrap_admin_creates_superuser_and_profile(monkeypatch):
    prompts = iter(("Unique-Admin-Phrase!2026", "Unique-Admin-Phrase!2026"))
    monkeypatch.setattr(
        "apps.accounts.management.commands.bootstrap_admin.getpass",
        lambda _prompt: next(prompts),
    )

    call_command(
        "bootstrap_admin",
        email="new.director@example.org",
        display_name="New Director",
        stdout=StringIO(),
    )

    admin = User.objects.get(email="new.director@example.org")
    assert admin.is_active and admin.is_staff and admin.is_superuser
    assert admin.email_verified
    assert admin.check_password("Unique-Admin-Phrase!2026")
    assert Profile.objects.get(user=admin).display_name == "New Director"
    assert not StaticDevice.objects.filter(user=admin).exists()


@pytest.mark.django_db
def test_bootstrap_admin_refuses_existing_account_without_modifying_it(monkeypatch):
    existing = User.objects.create_user(
        email="existing.director@example.org",
        password="Existing-User-Password!2026",
        is_staff=False,
        is_superuser=False,
    )
    original_password_hash = existing.password
    monkeypatch.setattr(
        "apps.accounts.management.commands.bootstrap_admin.getpass",
        lambda _prompt: pytest.fail("Existing accounts must be rejected before prompting."),
    )

    with pytest.raises(CommandError, match="No changes were made"):
        call_command("bootstrap_admin", email=existing.email, stdout=StringIO())

    existing.refresh_from_db()
    assert existing.password == original_password_hash
    assert not existing.is_staff
    assert not existing.is_superuser
