"""
Django Admin back-office for Dr. Violet's Nairobi & Embu 5-Day Practical Residency Blocks:
- Manage dates, campus location (Nairobi vs Embu), capacity, and USD 100 lunch/tea fee.
- Includes CSV export action (`export_catering_headcount_csv`) for the lunch-and-tea catering headcount.
"""
import csv

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from .models import ResidencyBlock, ResidencyRegistration


@admin.action(description="Export registered student list to CSV (Lunch & Tea Catering Headcount)")
def export_catering_headcount_csv(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: QuerySet[ResidencyBlock],
) -> HttpResponse:
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="residency_catering_headcount.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "Block Location",
            "Course Title",
            "Starts On",
            "Ends On",
            "Seat Number",
            "Student Name",
            "Student Email",
            "Registration Status",
            "Fee Paid (USD)",
            "Dietary Notes",
        ]
    )

    registrations = (
        ResidencyRegistration.objects.filter(
            block__in=queryset,
            status__in=[
                ResidencyRegistration.Status.CONFIRMED,
                ResidencyRegistration.Status.PENDING_PAYMENT,
            ],
        )
        .select_related(
            "block",
            "block__course",
            "enrollment__user",
            "enrollment__user__profile",
        )
        .order_by("block__starts_on", "block__location", "seat_number")
    )

    for reg in registrations:
        user = reg.enrollment.user
        profile = getattr(user, "profile", None)
        display_name = profile.display_name if profile and profile.display_name else user.email
        writer.writerow(
            [
                reg.block.get_location_display(),
                reg.block.course.title,
                reg.block.starts_on.isoformat(),
                reg.block.ends_on.isoformat(),
                reg.seat_number,
                display_name,
                user.email,
                reg.status,
                f"{reg.block.fee_major:.2f}",
                reg.dietary_notes,
            ]
        )

    return response


class ResidencyRegistrationInline(admin.TabularInline):
    model = ResidencyRegistration
    extra = 0
    readonly_fields = ("seat_number", "enrollment", "status", "payment", "dietary_notes", "created_at")


@admin.register(ResidencyBlock)
class ResidencyBlockAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "location",
        "course",
        "starts_on",
        "ends_on",
        "capacity",
        "fee_minor",
        "currency",
        "is_open",
    )
    list_filter = ("location", "is_open", "course")
    search_fields = ("title", "course__title", "location")
    inlines = (ResidencyRegistrationInline,)
    actions = [export_catering_headcount_csv]


@admin.register(ResidencyRegistration)
class ResidencyRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "enrollment",
        "block",
        "seat_number",
        "status",
        "dietary_notes",
        "created_at",
    )
    list_filter = ("status", "block__location", "block")
    search_fields = ("enrollment__user__email", "block__title", "dietary_notes")
    readonly_fields = ("id", "seat_number", "payment", "created_at", "updated_at")
