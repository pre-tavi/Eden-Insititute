"""
Root URL configuration for Eden Training Institute and Therapy (EdenLMS) Backend API.
Frontend SPA is served separately with zero cold start on Cloudflare Pages.
"""
from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django_otp.admin import OTPAdminSite

admin.site.site_header = "Eden Training Institute and Therapy — LMS Back-Office"
admin.site.site_title = "EdenLMS Instructor Admin"
admin.site.index_title = (
    "TVETA/PRIVATE/TVC/0019/2016 · KNEC Programmes, Cohorts, DPO Payments & Residency Blocks"
)

if getattr(settings, "ENFORCE_STAFF_2FA", False):
    admin.site.__class__ = OTPAdminSite


def api_root_index(request):
    """Root JSON service directory for the Render Backend API."""
    return JsonResponse(
        {
            "service": "Eden Training Institute and Therapy (EdenLMS) — Backend API",
            "license": "TVETA/PRIVATE/TVC/0019/2016",
            "campus": "Shepherds Building, Buruburu Phase II, Mumias South Road, Nairobi",
            "status": "online",
            "instructor_admin_url": f"/{settings.DJANGO_ADMIN_URL}",
            "endpoints": {
                "health": "/api/health/",
                "catalog": "/api/catalog/courses/",
                "auth_me": "/api/auth/me/",
                "enrollments": "/api/enrollments/",
                "residency_blocks": "/api/residency/blocks/",
            },
        }
    )


def api_root_health(request):
    """Lightweight health check endpoint for smoke testing and Render probes."""
    return JsonResponse(
        {
            "status": "ok",
            "service": "edenlms-api",
            "institution": "Eden Training Institute and Therapy",
            "license": "TVETA/PRIVATE/TVC/0019/2016",
        }
    )


urlpatterns = [
    path("", api_root_index, name="api-root-index"),
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    path("api/health/", api_root_health, name="api-health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/enrollments/", include("apps.enrollments.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/classroom/", include("apps.classroom.urls")),
    path("api/residency/", include("apps.residency.urls")),
]