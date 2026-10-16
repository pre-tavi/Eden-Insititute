"""
Explicit, tamper-resistant DRF serializers for DPO Pay initiation, verification, and receipts.
Complies with Pre-Deployment Security Checklist #8, #17, and #22:
- Never accepts price, amount_minor, currency, or status from the client.
- Trims raw_log out of student responses so internal gateway XML stays server-only.
"""
from rest_framework import serializers

from apps.enrollments.models import Enrollment

from .models import Payment


class PaymentReadSerializer(serializers.ModelSerializer):
    """Trimmed student receipt serializer (excludes internal raw_log)."""

    amount_major = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    provider_display = serializers.CharField(source="get_provider_display", read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "enrollment",
            "provider",
            "provider_display",
            "provider_ref",
            "company_ref",
            "amount_minor",
            "amount_major",
            "currency",
            "status",
            "status_display",
            "checkout_url",
            "verified_at",
            "created_at",
        )
        read_only_fields = fields

    def get_amount_major(self, obj: Payment) -> str:
        return f"{obj.amount_major:.2f}"


class PaymentInitiateSerializer(serializers.Serializer):
    """
    Validates a student's request to initiate DPO Pay checkout for their own Enrollment.
    Rejects any attempt to pass client-side price or currency overrides.
    """

    enrollment_id = serializers.UUIDField()

    def validate_enrollment_id(self, value) -> Enrollment:
        request = self.context["request"]
        try:
            enrollment = (
                Enrollment.objects.for_user(request.user)
                .select_related("cohort__course", "user__profile")
                .prefetch_related("cohort__course__prices")
                .get(pk=value)
            )
        except Enrollment.DoesNotExist as exc:
            raise serializers.ValidationError("Enrollment not found.") from exc

        if enrollment.status == Enrollment.Status.ACTIVE:
            raise serializers.ValidationError("This enrollment is already paid and active.")

        if enrollment.status != Enrollment.Status.PENDING_PAYMENT:
            raise serializers.ValidationError(
                f"Cannot initiate payment for an enrollment in '{enrollment.status}' status."
            )

        return enrollment


class PaymentVerifyReturnSerializer(serializers.Serializer):
    """
    Validates the DPO TransToken / ID parameter when a student returns from DPO hosted checkout.
    Actual payment status is verified server-to-server with DPO; browser flags are ignored.
    """

    provider_ref = serializers.CharField(max_length=128)

    def validate_provider_ref(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("A valid DPO transaction reference is required.")
        return cleaned