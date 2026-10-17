"""
Django Admin back-office for Dr. Violet to inspect student enrollments,
view per-student lesson progress percentages and residency status, export CSV reports,
and manually mark bank/M-Pesa edge-case enrollments as paid & active with an audit entry.
"""
import csv

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from apps.classroom.models import Lesson, LessonProgress
from apps.payments.services import record_manual_staff_payment

from .models import Enrollment


def compute_enrollment_progress_percent(enrollment: Enrollment) -> int:
    """Compute the student's completed lesson percentage for the enrolled course."""
    course = enrollment.cohort.course
    total_published = Lesson.objects.filter(
        module__course=course,
        is_published=True,
    ).count()
    if total_published == 0:
        return 100 if enrollment.status == Enrollment.Status.COMPLETED else 0

    completed = LessonProgress.objects.filter(
        user=enrollment.user,
        lesson__module__course=course,
        lesson__is_published=True,
        status=LessonProgress.Status.COMPLETED,
    ).count()
    return round((completed / total_published) * 100)


@admin.action(description="Mark selected enrollments as Paid & Active (Creates Audited Payment)")
def mark_enrollments_active_manually(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: QuerySet[Enrollment],
) -> None:
    activated_count = 0
    for enrollment in queryset:
        if enrollment.status != Enrollment.Status.ACTIVE:
            record_manual_staff_payment(
                enrollment=enrollment,
                staff_email=request.user.email,
                reference_note="Activated via EnrollmentAdmin manual action",
            )
            activated_count += 1

    modeladmin.message_user(
        request,
        f"Successfully recorded manual payment and activated {activated_count} enrollment(s).",
        messages.SUCCESS,
    )


@admin.action(description="Export selected student enrollments & progress percentages to CSV")
def export_enrollments_progress_csv(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: QuerySet[Enrollment],
) -> HttpResponse:
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="student_enrollments_progress.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Student Email",
            "Student Name",
            "Country",
            "Course Title",
            "Level",
            "Cohort",
            "Enrollment Status",
            "Progress (%)",
            "Activation Source",
            "Enrolled At",
        ]
    )

    records = queryset.select_related(
        "user",
        "user__profile",
        "cohort",
        "cohort__course",
    )
    for enrollment in records:
        profile = getattr(enrollment.user, "profile", None)
        display_name = profile.display_name if profile and profile.display_name else enrollment.user.email
        country = profile.country if profile else "KE"
        pct = compute_enrollment_progress_percent(enrollment)
        writer.writerow(
            [
                enrollment.user.email,
                display_name,
                country,
                enrollment.cohort.course.title,
                enrollment.cohort.course.level,
                enrollment.cohort.name,
                enrollment.status,
                f"{pct}%",
                enrollment.activation_source,
                enrollment.created_at.isoformat(),
            ]
        )

    return response


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "cohort",
        "status",
        "progress_percentage_display",
        "residency_status_display",
        "activation_source",
        "activated_at",
        "created_at",
    )
    list_filter = ("status", "cohort__course__level", "cohort")
    search_fields = (
        "user__email",
        "user__profile__display_name",
        "cohort__course__title",
    )
    readonly_fields = (
        "id",
        "progress_percentage_display",
        "residency_status_display",
        "activated_at",
        "completed_at",
        "activation_source",
        "created_at",
        "updated_at",
    )
    actions = [mark_enrollments_active_manually, export_enrollments_progress_csv]

    @admin.display(description="Progress %")
    def progress_percentage_display(self, obj: Enrollment) -> str:
        return f"{compute_enrollment_progress_percent(obj)}%"

    @admin.display(description="Residency Booking")
    def residency_status_display(self, obj: Enrollment) -> str:
        reg = obj.residency_registrations.select_related("block").first()
        if reg is None:
            return "None"
        return f"{reg.block.get_location_display()} (Seat #{reg.seat_number} · {reg.status})"