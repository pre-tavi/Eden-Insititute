"""
Public read-only API views for browsing published Courses and Course Details.
Explicitly opts into AllowAny while all private endpoints remain IsAuthenticated by default.
"""
from django.db.models import QuerySet
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import Course
from .serializers import CourseDetailSerializer, CourseListSerializer


class CourseListView(generics.ListAPIView):
    """
    GET /api/catalog/courses/
    Optional query parameter: ?level=certificate or ?level=diploma
    Returns only PUBLISHED courses with their local and international prices.
    """

    permission_classes = [AllowAny]
    serializer_class = CourseListSerializer

    def get_queryset(self) -> QuerySet[Course]:
        queryset = (
            Course.objects.filter(status=Course.Status.PUBLISHED)
            .prefetch_related("prices")
            .order_by("level", "title")
        )
        level = self.request.query_params.get("level")
        if level in (Course.Level.CERTIFICATE, Course.Level.DIPLOMA):
            queryset = queryset.filter(level=level)
        return queryset


class CourseDetailView(generics.RetrieveAPIView):
    """
    GET /api/catalog/courses/<slug:slug>/
    Returns full course details, local/international pricing, and open cohorts for a published course.
    """

    permission_classes = [AllowAny]
    serializer_class = CourseDetailSerializer
    lookup_field = "slug"

    def get_queryset(self) -> QuerySet[Course]:
        return (
            Course.objects.filter(status=Course.Status.PUBLISHED)
            .prefetch_related("prices", "cohorts")
        )
