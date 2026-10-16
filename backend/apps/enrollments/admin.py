"""
Django Admin back-office for Dr. Violet to inspect student enrollments
and manually mark bank/M-Pesa edge-case enrollments as active with an audit trail.
"""
from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Enrollment, activate_enrollment


@admin.action(description="Mark selected enrollments as Paid & Active (Manual Staff Override)")
def mark_enrollments_active_manually(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: QuerySet[Enrollment],
) -> None:
    activated_count = 0
    for enrollment in queryset:
        if enrollment.status != Enrollment.Status.ACTIVE:
            activate_enrollment(
                enrollment,
                source=f"staff_manual:{request.user.email}",
            )
            activated_count += 1

    modeladmin.message_user(
        request,
        f"Successfully activated {activated_count} student enrollment(s).",
        messages.SUCCESS,
    )


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "cohort",
        "status",
        "activation_source",
        "activated_at",
        "created_at",
    )
    list_filter = ("status", "cohort__course__level", "cohort")
    search_fields = ("user__email", "user__profile__display_name", "cohort__course__title")
    readonly_fields = (
        "id",
        "activated_at",
        "completed_at",
        "activation_source",
        "created_at",
        "updated_at",
    )
    actions = [mark_enrollments_active_manually]