"""
Explicit, tamper-resistant DRF serializers for Nairobi & Embu 5-Day Practical Residency Blocks.
Complies with Blueprint Phase 5 and Pre-Deployment Security Checklist #8 & #17.
"""
from rest_framework import serializers

from apps.payments.serializers import PaymentReadSerializer

from .models import RESIDENCY_CATERING_NOTICE, ResidencyBlock, ResidencyRegistration


class ResidencyBlockSerializer(serializers.ModelSerializer):
    """Serializes a 5-day Nairobi or Embu practical block with remaining seat count and USD 100 fee."""

    location_display = serializers.CharField(source="get_location_display", read_only=True)
    fee_major = serializers.SerializerMethodField()
    seats_remaining = serializers.SerializerMethodField()
    catering_notice = serializers.SerializerMethodField()

    class Meta:
        model = ResidencyBlock
        fields = (
            "id",
            "course",
            "location",
            "location_display",
            "title",
            "starts_on",
            "ends_on",
            "capacity",
            "seats_remaining",
            "fee_minor",
            "fee_major",
            "currency",
            "catering_notice",
            "is_open",
        )
        read_only_fields = fields

    def get_fee_major(self, obj: ResidencyBlock) -> str:
        return f"{obj.fee_major:.2f}"

    def get_seats_remaining(self, obj: ResidencyBlock) -> int:
        taken = obj.registrations.filter(
            status__in=[
                ResidencyRegistration.Status.PENDING_PAYMENT,
                ResidencyRegistration.Status.CONFIRMED,
            ]
        ).count()
        return max(0, obj.capacity - taken)

    def get_catering_notice(self, obj: ResidencyBlock) -> str:
        return RESIDENCY_CATERING_NOTICE


class ResidencyRegistrationReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for a student's ResidencyRegistration and linked DPO payment."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    block = ResidencyBlockSerializer(read_only=True)
    payment = PaymentReadSerializer(read_only=True)
    catering_notice = serializers.SerializerMethodField()

    class Meta:
        model = ResidencyRegistration
        fields = (
            "id",
            "enrollment",
            "block",
            "seat_number",
            "status",
            "status_display",
            "payment",
            "dietary_notes",
            "catering_notice",
            "created_at",
        )
        read_only_fields = fields

    def get_catering_notice(self, obj: ResidencyRegistration) -> str:
        return RESIDENCY_CATERING_NOTICE


class ResidencyBookingCreateSerializer(serializers.Serializer):
    """Validates a student's request to book a 5-day practical block in Nairobi or Embu."""

    block_id = serializers.UUIDField()
    dietary_notes = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")