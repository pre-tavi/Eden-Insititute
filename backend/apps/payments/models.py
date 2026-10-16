"""
Payment domain model and row-isolated queryset manager for Dr. Violet's LMS (EdenLMS).
Complies with Blueprint Section 4, Phase 3, and Pre-Deployment Security Checklist #4, #8, and #22.
"""
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.catalog.models import Price
from apps.enrollments.models import Enrollment


class PaymentQuerySet(models.QuerySet):
    """Custom QuerySet enforcing per-student record isolation."""

    def for_user(self, user) -> "PaymentQuerySet":
        """
        Scope payment records strictly to the authenticated student.
        Returns an empty queryset for anonymous users.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(enrollment__user=user)


class PaymentManager(models.Manager.from_queryset(PaymentQuerySet)):
    """Default manager exposing .for_user(request.user) on Payment.objects."""


class Payment(models.Model):
    """
    Immutable financial ledger entry for a course Enrollment (or future ResidencyRegistration).
    Enforces UNIQUE(provider, provider_ref) for idempotent webhook & return handling.
    Money is stored strictly as integer minor units (amount_minor) + ISO currency code.
    """

    class Provider(models.TextChoices):
        DPO = "dpo", "DPO Pay"
        MANUAL = "manual", "Staff Manual Override (Bank / M-Pesa)"

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated (Awaiting Checkout)"
        VERIFIED = "verified", "Verified & Paid"
        FAILED = "failed", "Failed / Declined"
        TAMPERED = "tampered", "Rejected (Amount or Currency Mismatch)"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name="payments",
        null=True,
        blank=True,
    )
    provider = models.CharField(
        max_length=24,
        choices=Provider.choices,
        default=Provider.DPO,
        db_index=True,
    )
    provider_ref = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Unique transaction token/reference from the payment provider (e.g., DPO TransToken).",
    )
    company_ref = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Internal EdenLMS idempotency reference sent to DPO as CompanyRef.",
    )
    amount_minor = models.PositiveBigIntegerField(
        help_text="Server-computed amount in minor units (e.g., KES 35,000 = 3500000; USD 550 = 55000).",
    )
    currency = models.CharField(
        max_length=3,
        choices=Price.Currency.choices,
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.INITIATED,
        db_index=True,
    )
    checkout_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Hosted DPO Pay redirect URL.",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    raw_log = models.JSONField(
        default=dict,
        blank=True,
        help_text="Audit log of raw provider responses, webhook payloads, or manual staff notes.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PaymentManager()

    class Meta:
        db_table = "payments_payment"
        ordering = ["-created_at"]
        verbose_name = "payment"
        verbose_name_plural = "payments"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_ref"],
                name="unique_payment_provider_ref",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.amount_minor <= 0:
            raise ValidationError({"amount_minor": "Payment amount_minor must be greater than zero."})

    @property
    def amount_major(self) -> Decimal:
        """Exact Decimal representation in major currency units (amount_minor / 100)."""
        return (Decimal(self.amount_minor) / Decimal(100)).quantize(Decimal("0.01"))

    def __str__(self) -> str:
        return f"{self.provider.upper()}:{self.provider_ref} — {self.currency} {self.amount_major:,.2f} [{self.status}]"