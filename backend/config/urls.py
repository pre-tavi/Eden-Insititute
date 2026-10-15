"""Root URL configuration for Dr. Violet's LMS (EdenLMS)."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root_health(request):
    """Lightweight health check endpoint for smoke testing and uptime probes."""
    return JsonResponse({"status": "ok", "service": "edenlms-api"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", api_root_health, name="api-health"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/enrollments/", include("apps.enrollments.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/classroom/", include("apps.classroom.urls")),
    path("api/residency/", include("apps.residency.urls")),
]