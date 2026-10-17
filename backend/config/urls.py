"""
Root URL configuration for Dr. Violet's LMS (EdenLMS).
Complies with Blueprint Phase 6 and Pre-Deployment Security Checklist #21:
- Supports configurable non-default admin URL (`settings.DJANGO_ADMIN_URL`).
- Enforces TOTP 2FA (`OTPAdminSite`) for staff accounts when `settings.ENFORCE_STAFF_2FA` is enabled.
"""
from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django_otp.admin import OTPAdminSite

admin.site.site_header = "Dr. Violet's Institute of Psychology — LMS Back-Office"
admin.site.site_title = "EdenLMS Instructor Admin"
admin.site.index_title = "Academic Programmes, Cohorts, DPO Payments & Residency Blocks"

if getattr(settings, "ENFORCE_STAFF_2FA", False):
    admin.site.__class__ = OTPAdminSite


def api_root_health(request):
    """Lightweight health check endpoint for smoke testing and uptime probes."""
    return JsonResponse({"status": "ok", "service": "edenlms-api"})


urlpatterns = [
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    path("api/health/", api_root_health, name="api-health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/enrollments/", include("apps.enrollments.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/classroom/", include("apps.classroom.urls")),
    path("api/residency/", include("apps.residency.urls")),
]