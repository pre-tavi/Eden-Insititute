"""
API views for DPO Pay checkout initiation, browser return verification, and server-to-server
webhook notifications.
Complies with Blueprint Phase 3 and Pre-Deployment Security Checklist #4, #7, #8, and #22.
"""
from defusedxml import ElementTree as SafeET
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Payment
from .serializers import (
    PaymentInitiateSerializer,
    PaymentReadSerializer,
    PaymentVerifyReturnSerializer,
)
from .services import (
    PaymentIntegrationError,
    initiate_enrollment_payment,
    verify_and_activate_dpo_payment,
)

CLIENT_FORBIDDEN_PRICE_FIELDS = frozenset(
    {"amount", "amount_minor", "amount_major", "price", "currency", "status", "audience"}
)


class PaymentListView(generics.ListAPIView):
    """
    GET /api/payments/
    Lists only the authenticated student's payments and receipts.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentReadSerializer

    def get_queryset(self) -> QuerySet[Payment]:
        return (
            Payment.objects.for_user(self.request.user)
            .select_related("enrollment", "enrollment__cohort__course")
            .order_by("-created_at")
        )


class PaymentDetailView(generics.RetrieveAPIView):
    """
    GET /api/payments/<uuid:pk>/
    Retrieves a single payment receipt scoped strictly to request.user (returns 404 for other students).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentReadSerializer

    def get_object(self) -> Payment:
        queryset = Payment.objects.for_user(self.request.user).select_related(
            "enrollment", "enrollment__cohort__course"
        )
        return get_object_or_404(queryset, pk=self.kwargs["pk"])


class PaymentInitiateView(APIView):
    """
    POST /api/payments/initiate/
    Creates or reuses an INITIATED DPO payment using the server-computed price for the student's
    audience ('local' KES vs 'international' USD) and returns the hosted DPO checkout URL.
    Rejects any payload that attempts to pass client-side price or currency fields.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    def post(self, request: Request) -> Response:
        if isinstance(request.data, dict):
            forbidden = set(request.data.keys()) & CLIENT_FORBIDDEN_PRICE_FIELDS
            if forbidden:
                return Response(
                    {
                        "detail": (
                            "Client-supplied price or status fields "
                            f"({', '.join(sorted(forbidden))}) are forbidden. "
                            "Tuition is computed strictly on the server."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = PaymentInitiateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.validated_data["enrollment_id"]

        origin = request.build_absolute_uri("/").rstrip("/")
        redirect_url = f"{origin}/my-learning?dpo_return=1"
        back_url = f"{origin}/my-learning"

        try:
            payment = initiate_enrollment_payment(
                enrollment=enrollment,
                redirect_url=redirect_url,
                back_url=back_url,
            )
        except (DjangoValidationError, PaymentIntegrationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            PaymentReadSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )


class PaymentVerifyReturnView(APIView):
    """
    POST /api/payments/verify-return/
    Triggered when a student returns from DPO hosted checkout.
    Ignores everything the browser claims about payment success; performs a server-to-server
    verification against DPO before marking the payment verified and activating the enrollment.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "payment"

    def post(self, request: Request) -> Response:
        serializer = PaymentVerifyReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider_ref = serializer.validated_data["provider_ref"]

        get_object_or_404(
            Payment.objects.for_user(request.user),
            provider=Payment.Provider.DPO,
            provider_ref=provider_ref,
        )

        try:
            verified_payment = verify_and_activate_dpo_payment(
                provider_ref=provider_ref,
                trigger_source=f"student_return:{request.user.email}",
            )
        except (DjangoValidationError, PaymentIntegrationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            PaymentReadSerializer(verified_payment).data,
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name="dispatch")
class DpoWebhookNotificationView(APIView):
    """
    POST /api/payments/webhook/dpo/
    Server-to-server notification endpoint called by DPO Pay (supports XML, JSON, or form payloads).
    Accepts arbitrary content types (JSON, XML, text/plain, form-urlencoded) to prevent 415 errors.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request: Request) -> Response:
        provider_ref = ""

        if isinstance(request.data, dict):
            provider_ref = str(
                request.data.get("TransToken")
                or request.data.get("TransactionToken")
                or request.data.get("provider_ref")
                or request.data.get("ID")
                or ""
            ).strip()

        if not provider_ref and request.body:
            raw_body = request.body.decode("utf-8", errors="replace").strip()
            if raw_body.startswith("<"):
                try:
                    parsed = SafeET.fromstring(raw_body)
                    provider_ref = (
                        parsed.findtext("TransactionToken")
                        or parsed.findtext("TransToken")
                        or ""
                    ).strip()
                except Exception:
                    provider_ref = ""

        if not provider_ref:
            return Response(
                {"detail": "Missing DPO TransactionToken / provider_ref."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = verify_and_activate_dpo_payment(
                provider_ref=provider_ref,
                trigger_source="dpo_server_webhook",
            )
        except (DjangoValidationError, PaymentIntegrationError) as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "ok",
                "payment_id": str(payment.id),
                "payment_status": payment.status,
            },
            status=status.HTTP_200_OK,
        )