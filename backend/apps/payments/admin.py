"""
Django Admin back-office for Dr. Violet's Payment Ledger:
- Inspect DPO Pay statuses, currencies, integer minor-unit amounts, and raw_log audit JSON.
- Includes a 'Mark as Paid Manually' action that verifies the payment, writes an audit entry
  in Payment.raw_log, and calls activate_enrollment().
"""
from datetime import UTC, datetime

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone

from apps.enrollments.models import activate_enrollment

from .models import Payment


@admin.action(description="Mark selected payments as Paid Manually (Audited Staff Override)")
def mark_payments_paid_manually(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: QuerySet[Payment],
) -> None:
    updated_count = 0
    for payment in queryset.select_related("enrollment"):
        if payment.status == Payment.Status.VERIFIED:
            continue

        raw_log = dict(payment.raw_log or {})
        manual_entries = list(raw_log.get("manual_audit", []))
        manual_entries.append(
            {
                "action": "mark_paid_manually",
                "staff_email": request.user.email,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )
        raw_log["manual_audit"] = manual_entries

        payment.status = Payment.Status.VERIFIED
        payment.verified_at = timezone.now()
        payment.raw_log = raw_log
        payment.save(update_fields=["status", "verified_at", "raw_log", "updated_at"])

        if payment.enrollment is not None:
            activate_enrollment(
                payment.enrollment,
                source=f"staff_manual_payment:{request.user.email}",
            )
        updated_count += 1

    modeladmin.message_user(
        request,
        f"Marked {updated_count} payment(s) as verified and activated linked enrollment(s).",
        messages.SUCCESS,
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "provider_ref",
        "provider",
        "enrollment",
        "currency",
        "amount_minor",
        "status",
        "verified_at",
        "created_at",
    )
    list_filter = ("status", "provider", "currency")
    search_fields = (
        "provider_ref",
        "company_ref",
        "enrollment__user__email",
        "enrollment__cohort__course__title",
    )
    readonly_fields = (
        "id",
        "provider_ref",
        "company_ref",
        "amount_minor",
        "currency",
        "verified_at",
        "raw_log",
        "created_at",
        "updated_at",
    )
    actions = [mark_payments_paid_manually]