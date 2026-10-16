"""URL routes for the DPO Pay payments app."""
from django.urls import path

from .views import (
    DpoWebhookNotificationView,
    PaymentDetailView,
    PaymentInitiateView,
    PaymentListView,
    PaymentVerifyReturnView,
)

app_name = "payments"

urlpatterns = [
    path("", PaymentListView.as_view(), name="payment-list"),
    path("initiate/", PaymentInitiateView.as_view(), name="payment-initiate"),
    path(
        "verify-return/",
        PaymentVerifyReturnView.as_view(),
        name="payment-verify-return",
    ),
    path(
        "webhook/dpo/",
        DpoWebhookNotificationView.as_view(),
        name="dpo-webhook",
    ),
    path("<uuid:pk>/", PaymentDetailView.as_view(), name="payment-detail"),
]