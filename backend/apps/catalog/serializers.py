"""
Explicit, trimmed read-only serializers for the public Catalog and Course Detail screens.
Complies with Pre-Deployment Security Checklist #8 (Block field tampering) and #17 (Trim API responses).
"""
from django.db.models import QuerySet
from rest_framework import serializers

from .models import Cohort, Course, Price


class PriceSerializer(serializers.ModelSerializer):
    """Serializes explicit integer minor-unit course prices per audience tier."""

    amount_major = serializers.SerializerMethodField()

    class Meta:
        model = Price
        fields = (
            "id",
            "audience",
            "currency",
            "amount_minor",
            "amount_major",
        )
        read_only_fields = fields

    def get_amount_major(self, obj: Price) -> str:
        return f"{obj.amount_major:.2f}"


class CohortPublicSerializer(serializers.ModelSerializer):
    """Serializes public intake cohort metadata for the Course Detail screen."""

    class Meta:
        model = Cohort
        fields = (
            "id",
            "name",
            "starts_on",
            "capacity",
            "enrollment_open",
        )
        read_only_fields = fields


class CourseListSerializer(serializers.ModelSerializer):
    """Trimmed serializer for Catalog cards (excludes full syllabus description)."""

    level_display = serializers.CharField(source="get_level_display", read_only=True)
    residency_display = serializers.CharField(source="get_residency_display", read_only=True)
    prices = PriceSerializer(many=True, read_only=True)

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
            "prices",
        )
        read_only_fields = fields


class CourseDetailSerializer(serializers.ModelSerializer):
    """Full Course Detail serializer including syllabus outline, prices, and open cohorts."""

    level_display = serializers.CharField(source="get_level_display", read_only=True)
    residency_display = serializers.CharField(source="get_residency_display", read_only=True)
    prices = PriceSerializer(many=True, read_only=True)
    cohorts = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "description",
            "level",
            "level_display",
            "residency",
            "residency_display",
            "prices",
            "cohorts",
        )
        read_only_fields = fields

    def get_cohorts(self, obj: Course) -> list[dict]:
        open_cohorts: QuerySet[Cohort] = obj.cohorts.filter(enrollment_open=True).order_by("starts_on")
        return CohortPublicSerializer(open_cohorts, many=True).data