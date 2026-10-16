"""
Authenticated, user-scoped Enrollment API views.
Enforces row-level isolation via Enrollment.objects.for_user(request.user) and blocks field tampering.
"""
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Enrollment
from .serializers import EnrollmentCreateSerializer, EnrollmentReadSerializer

TAMPER_PROTECTED_FIELDS = frozenset(
    {
        "status",
        "paid_at",
        "activated_at",
        "completed_at",
        "price",
        "amount_minor",
        "is_staff",
        "role",
        "user",
    }
)


class EnrollmentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/enrollments/ -> Lists only the authenticated student's enrollments.
    POST /api/enrollments/ -> Creates a PENDING_PAYMENT enrollment for an open cohort.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = EnrollmentReadSerializer

    def get_queryset(self) -> QuerySet[Enrollment]:
        return (
            Enrollment.objects.for_user(self.request.user)
            .select_related("cohort", "cohort__course", "user__profile")
            .prefetch_related("cohort__course__prices")
            .order_by("-created_at")
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        create_serializer = EnrollmentCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        create_serializer.is_valid(raise_exception=True)
        enrollment = create_serializer.save()
        read_serializer = EnrollmentReadSerializer(enrollment)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class EnrollmentDetailView(generics.RetrieveAPIView):
    """
    GET   /api/enrollments/<uuid:pk>/ -> Fetches a single enrollment scoped strictly to request.user.
    PATCH /api/enrollments/<uuid:pk>/ -> Rejects any attempt by a student to tamper with status or price.
    Student A requesting or mutating Student B's enrollment always receives HTTP 404.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = EnrollmentReadSerializer

    def get_object(self) -> Enrollment:
        queryset = (
            Enrollment.objects.for_user(self.request.user)
            .select_related("cohort", "cohort__course", "user__profile")
            .prefetch_related("cohort__course__prices")
        )
        return get_object_or_404(queryset, pk=self.kwargs["pk"])

    def patch(self, request: Request, *args, **kwargs) -> Response:
        enrollment = self.get_object()
        attempted_fields = set(request.data.keys()) & TAMPER_PROTECTED_FIELDS
        if attempted_fields:
            return Response(
                {
                    "detail": (
                        "Direct modification of protected enrollment fields "
                        f"({', '.join(sorted(attempted_fields))}) is forbidden."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            EnrollmentReadSerializer(enrollment).data,
            status=status.HTTP_200_OK,
        )