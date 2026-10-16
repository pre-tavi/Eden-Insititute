"""
Tamper-resistant serializers for creating and viewing student Enrollments.
Complies with Pre-Deployment Security Checklist #8 (Block field tampering) and #17 (Trim API responses).
"""
from rest_framework import serializers

from apps.catalog.models import Cohort, Course
from apps.catalog.serializers import CohortPublicSerializer, PriceSerializer

from .models import Enrollment


class CourseEnrollmentSummarySerializer(serializers.ModelSerializer):
    """Trimmed course summary embedded inside a student's Enrollment card."""

    level_display = serializers.CharField(source="get_level_display", read_only=True)
    residency_display = serializers.CharField(source="get_residency_display", read_only=True)

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "level",
            "level_display",
            "residency",
            "residency_display",
        )
        read_only_fields = fields


class EnrollmentReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for student Enrollment records.
    Status, timestamps, cohort, and server-computed price cannot be modified by the client.
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    cohort = CohortPublicSerializer(read_only=True)
    course = CourseEnrollmentSummarySerializer(source="cohort.course", read_only=True)
    expected_price = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "status",
            "status_display",
            "cohort",
            "course",
            "expected_price",
            "activated_at",
            "completed_at",
            "created_at",
        )
        read_only_fields = fields

    def get_expected_price(self, obj: Enrollment) -> dict | None:
        price = obj.get_server_price()
        if price is None:
            return None
        return PriceSerializer(price).data


class EnrollmentCreateSerializer(serializers.Serializer):
    """
    Validates a student's request to enroll in an open Cohort.
    Always initializes Enrollment with status='pending_payment'.
    """

    cohort_id = serializers.UUIDField()

    def validate_cohort_id(self, value) -> Cohort:
        try:
            cohort = Cohort.objects.select_related("course").get(pk=value)
        except Cohort.DoesNotExist as exc:
            raise serializers.ValidationError("Selected cohort does not exist.") from exc

        if cohort.course.status != Course.Status.PUBLISHED:
            raise serializers.ValidationError("This course is not open for enrollment.")

        if not cohort.enrollment_open:
            raise serializers.ValidationError("Enrollment for this cohort is currently closed.")

        active_or_pending_count = Enrollment.objects.filter(
            cohort=cohort,
            status__in=[
                Enrollment.Status.PENDING_PAYMENT,
                Enrollment.Status.ACTIVE,
                Enrollment.Status.COMPLETED,
            ],
        ).count()
        if active_or_pending_count >= cohort.capacity:
            raise serializers.ValidationError("This cohort has reached full capacity.")

        return cohort

    def validate(self, attrs: dict) -> dict:
        request = self.context["request"]
        cohort: Cohort = attrs["cohort_id"]

        if Enrollment.objects.filter(user=request.user, cohort=cohort).exists():
            raise serializers.ValidationError(
                {"cohort_id": "You already have an enrollment for this cohort."}
            )

        attrs["cohort"] = cohort
        return attrs

    def create(self, validated_data: dict) -> Enrollment:
        request = self.context["request"]
        cohort: Cohort = validated_data["cohort"]
        return Enrollment.objects.create(
            user=request.user,
            cohort=cohort,
            status=Enrollment.Status.PENDING_PAYMENT,
        )