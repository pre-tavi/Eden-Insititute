
"""
Phase 0 Smoke Test Suite for Dr. Violet's LMS (EdenLMS).
Verifies custom User Argon2 hashing, server-side audience rules, residency choices,
integer minor-unit pricing, and public catalog endpoints.
"""
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.catalog.models import Cohort, Course, Price

User = get_user_model()


@pytest.mark.django_db
def test_health_endpoint_returns_200():
    client = APIClient()
    response = client.get(reverse("api-health"))
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "edenlms-api",
        "institution": "Eden Training Institute and Therapy",
        "license": "TVETA/PRIVATE/TVC/0019/2016",
    }


@pytest.mark.django_db
def test_custom_user_uses_argon2_and_profile_computes_audience():
    user = User.objects.create_user(
        email="student.kenya@example.com",
        password="ComplexPassword!2026",
    )
    # Pre-Deployment Security Checklist #10: Argon2id must be primary password hasher
    assert user.password.startswith("argon2$")
    assert user.check_password("ComplexPassword!2026") is True

    profile_ke = Profile.objects.create(
        user=user,
        display_name="Amina Wanjiku",
        country="KE",
        timezone="Africa/Nairobi",
    )
    assert profile_ke.effective_audience == Profile.AudienceOverride.LOCAL

    # International student defaults to international pricing unless overridden by staff
    user_intl = User.objects.create_user(
        email="student.uk@example.com",
        password="ComplexPassword!2026",
    )
    profile_uk = Profile.objects.create(
        user=user_intl,
        display_name="Oliver Smith",
        country="GB",
        timezone="Europe/London",
    )
    assert profile_uk.effective_audience == Profile.AudienceOverride.INTERNATIONAL


@pytest.mark.django_db
def test_catalog_list_and_detail_endpoints_with_dr_violet_pricing():
    # 1. Certificate course with optional 5-day Nairobi/Embu residency
    cert_course = Course.objects.create(
        title="Certificate in Counselling Psychology",
        slug="certificate-counselling-psychology",
        summary="Foundational clinical and counselling psychology programme with live lectures.",
        description="Includes weekly live lectures and an optional 5-day practical block in Nairobi or Embu.",
        level=Course.Level.CERTIFICATE,
        residency=Course.Residency.OPTIONAL,
        status=Course.Status.PUBLISHED,
    )
    # Local fee: KES 35,000 -> 3,500,000 minor units; International fee: USD 550 -> 55,000 minor units
    Price.objects.create(
        course=cert_course,
        audience=Price.Audience.LOCAL,
        currency=Price.Currency.KES,
        amount_minor=3_500_000,
    )
    Price.objects.create(
        course=cert_course,
        audience=Price.Audience.INTERNATIONAL,
        currency=Price.Currency.USD,
        amount_minor=55_000,
    )
    Cohort.objects.create(
        course=cert_course,
        name="January 2027 Intake",
        starts_on=date(2027, 1, 15),
        capacity=30,
        enrollment_open=True,
    )

    # 2. Diploma course (Published) — Local KES 130,000 / International USD 1,800
    diploma_course = Course.objects.create(
        title="Diploma in Clinical & Applied Psychology",
        slug="diploma-clinical-applied-psychology",
        summary="Advanced diploma programme with supervised practical residency.",
        level=Course.Level.DIPLOMA,
        residency=Course.Residency.REQUIRED,
        status=Course.Status.PUBLISHED,
    )
    Price.objects.create(
        course=diploma_course,
        audience=Price.Audience.LOCAL,
        currency=Price.Currency.KES,
        amount_minor=13_000_000,
    )
    Price.objects.create(
        course=diploma_course,
        audience=Price.Audience.INTERNATIONAL,
        currency=Price.Currency.USD,
        amount_minor=180_000,
    )

    # 3. Draft course (Must never leak into public API responses)
    Course.objects.create(
        title="Unpublished Draft Course",
        slug="unpublished-draft-course",
        level=Course.Level.CERTIFICATE,
        residency=Course.Residency.NONE,
        status=Course.Status.DRAFT,
    )

    client = APIClient()

    # Verify list endpoint excludes drafts and returns published courses
    list_response = client.get(reverse("catalog:course-list"))
    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["count"] == 2

    # Verify filtering by level (?level=certificate)
    cert_filter_response = client.get(
        reverse("catalog:course-list"), {"level": "certificate"}
    )
    assert cert_filter_response.status_code == 200
    assert cert_filter_response.json()["count"] == 1
    assert (
        cert_filter_response.json()["results"][0]["slug"]
        == "certificate-counselling-psychology"
    )
    assert cert_filter_response.json()["results"][0]["residency"] == "optional"

    # Verify detail endpoint returns prices and open cohorts
    detail_response = client.get(
        reverse("catalog:course-detail", kwargs={"slug": "certificate-counselling-psychology"})
    )
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert detail_data["title"] == "Certificate in Counselling Psychology"
    assert len(detail_data["prices"]) == 2
    assert len(detail_data["cohorts"]) == 1
    assert detail_data["cohorts"][0]["name"] == "January 2027 Intake"
