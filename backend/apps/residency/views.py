"""
Authenticated API views for browsing and booking 5-day Practical Residency Blocks
in Nairobi and Embu ($100 USD lunch & tea fee).
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ResidencyBlock, ResidencyRegistration
from .serializers import (
    ResidencyBlockSerializer,
    ResidencyBookingCreateSerializer,
    ResidencyRegistrationReadSerializer,
)
from .services import book_residency_block


class ResidencyBlockListView(generics.ListAPIView):
    """
    GET /api/residency/blocks/?course_slug=<slug>
    Lists open 5-day Nairobi and Embu practical blocks for authenticated students.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ResidencyBlockSerializer

    def get_queryset(self) -> QuerySet[ResidencyBlock]:
        queryset = (
            ResidencyBlock.objects.filter(is_open=True)
            .select_related("course")
            .prefetch_related("registrations")
            .order_by("starts_on", "location")
        )
        course_slug = self.request.query_params.get("course_slug")
        if course_slug:
            queryset = queryset.filter(course__slug=course_slug)
        return queryset


class ResidencyRegistrationListCreateView(APIView):
    """
    GET  /api/residency/registrations/ -> Lists the authenticated student's residency bookings.
    POST /api/residency/registrations/ -> Atomically locks a seat in a Nairobi or Embu block
                                          and creates the $100 USD DPO Payment.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        registrations = (
            ResidencyRegistration.objects.for_user(request.user)
            .select_related("block", "block__course", "payment", "enrollment")
            .order_by("-created_at")
        )
        return Response(
            ResidencyRegistrationReadSerializer(registrations, many=True).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request: Request) -> Response:
        serializer = ResidencyBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        origin = request.build_absolute_uri("/").rstrip("/")
        redirect_url = f"{origin}/my-learning?residency_return=1"
        back_url = f"{origin}/my-learning"

        try:
            registration = book_residency_block(
                user=request.user,
                block_id=serializer.validated_data["block_id"],
                dietary_notes=serializer.validated_data.get("dietary_notes", ""),
                redirect_url=redirect_url,
                back_url=back_url,
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if hasattr(exc, "messages") and exc.messages else str(exc)
            return Response(
                {"detail": message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            ResidencyRegistrationReadSerializer(registration).data,
            status=status.HTTP_201_CREATED,
        )