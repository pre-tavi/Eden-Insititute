"""
Residency domain models for Dr. Violet's LMS (EdenLMS):
ResidencyBlock and ResidencyRegistration.
Complies with Blueprint Section 4 & Phase 5:
- 5-day practical blocks in Nairobi and Embu.
- USD 100 fee (10000 minor units) covering lunch and teas; travel and lodging are the student's responsibility.
- Database-enforced seat capacity via select_for_update() + UniqueConstraint on (block, seat_number).
"""
import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.catalog.models import Course, Price
from apps.enrollments.models import Enrollment
from apps.payments.models import Payment

RESIDENCY_CATERING_NOTICE = (
    "The $100 USD practical block fee covers daily lunch and teas in Nairobi or Embu. "
    "Travel and lodging are the student's responsibility."
)


class ResidencyBlock(models.Model):
    """
    Scheduled 5-day in-person practical residency block in Nairobi or Embu.
    """

    class Location(models.TextChoices):
        NAIROBI = "nairobi", "Nairobi Campus"
        EMBU = "embu", "Embu Campus"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="residency_blocks",
    )
    location = models.CharField(
        max_length=20,
        choices=Location.choices,
        db_index=True,
    )
    title = models.CharField(
        max_length=200,
        default="5-Day Practical Clinical Residency Block",
    )
    starts_on = models.DateField(db_index=True)
    ends_on = models.DateField()
    capacity = models.PositiveIntegerField(default=20)
    fee_minor = models.PositiveBigIntegerField(
        default=10_000,
        help_text="Residency fee in minor USD units (USD 100.00 = 10000) covering lunch and teas.",
    )
    currency = models.CharField(
        max_length=3,
        choices=Price.Currency.choices,
        default=Price.Currency.USD,
    )
    is_open = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "residency_block"
        ordering = ["starts_on", "location"]
        verbose_name = "residency block"
        verbose_name_plural = "residency blocks"

    def clean(self) -> None:
        super().clean()
        if self.capacity <= 0:
            raise ValidationError({"capacity": "Residency block capacity must be at least 1."})
        if self.starts_on and self.ends_on:
            expected_end = self.starts_on + timedelta(days=4)
            if self.ends_on < self.starts_on:
                raise ValidationError({"ends_on": "End date cannot be earlier than start date."})
            if (self.ends_on - self.starts_on).days != 4:
                raise ValidationError(
                    {"ends_on": f"A 5-day practical block starting {self.starts_on} must end on {expected_end}."}
                )

    @property
    def fee_major(self) -> Decimal:
        return (Decimal(self.fee_minor) / Decimal(100)).quantize(Decimal("0.01"))

    @property
    def catering_notice(self) -> str:
        return RESIDENCY_CATERING_NOTICE

    def __str__(self) -> str:
        return f"{self.get_location_display()} ({self.starts_on} to {self.ends_on}) — {self.course.title}"


class ResidencyRegistrationQuerySet(models.QuerySet):
    """Custom QuerySet enforcing per-student record isolation."""

    def for_user(self, user) -> "ResidencyRegistrationQuerySet":
        if not user or not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(enrollment__user=user)


class ResidencyRegistrationManager(models.Manager.from_queryset(ResidencyRegistrationQuerySet)):
    """Default manager exposing .for_user(request.user) on ResidencyRegistration.objects."""


class ResidencyRegistration(models.Model):
    """
    Student booking for a 5-day Nairobi or Embu ResidencyBlock.
    Enforces seat capacity via `seat_number` (1..block.capacity) and a partial UniqueConstraint
    on active bookings so concurrent requests can never overbook the final seat.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending $100 USD Payment"
        CONFIRMED = "confirmed", "Confirmed (Paid)"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="residency_registrations",
    )
    block = models.ForeignKey(
        ResidencyBlock,
        on_delete=models.PROTECT,
        related_name="registrations",
    )
    seat_number = models.PositiveIntegerField(
        help_text="Allocated seat number (1..capacity) locked inside a database transaction.",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="residency_registration",
    )
    dietary_notes = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional dietary notes for lunch and tea catering.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ResidencyRegistrationManager()

    class Meta:
        db_table = "residency_registration"
        ordering = ["block__starts_on", "seat_number"]
        verbose_name = "residency registration"
        verbose_name_plural = "residency registrations"
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "block"],
                name="unique_enrollment_residency_block",
            ),
            models.UniqueConstraint(
                fields=["block", "seat_number"],
                condition=Q(status__in=["pending_payment", "confirmed"]),
                name="unique_active_block_seat_number",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.enrollment.user.email} -> {self.block.get_location_display()} "
            f"[Seat #{self.seat_number} · {self.status}]"
        )