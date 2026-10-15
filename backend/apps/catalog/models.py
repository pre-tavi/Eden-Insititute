"""
Catalog domain models for Dr. Violet's LMS (EdenLMS): Course, Price, and Cohort.
Enforces UUID primary keys, three-state residency rules, and integer minor-unit pricing.
"""
import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class Course(models.Model):
    """
    Sellable academic programme (Certificate or Diploma in Psychology).
    """

    class Level(models.TextChoices):
        CERTIFICATE = "certificate", "Certificate"
        DIPLOMA = "diploma", "Diploma"

    class Residency(models.TextChoices):
        NONE = "none", "100% Online (No Residency)"
        OPTIONAL = "optional", "Optional 5-Day Practical Block (Nairobi / Embu)"
        REQUIRED = "required", "Required 5-Day Practical Block (Nairobi / Embu)"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    summary = models.CharField(
        max_length=320,
        blank=True,
        help_text="Short card summary shown in the student catalog.",
    )
    description = models.TextField(
        blank=True,
        help_text="Full course overview, syllabus outline, and live lecture expectations.",
    )
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.CERTIFICATE,
        db_index=True,
    )
    residency = models.CharField(
        max_length=20,
        choices=Residency.choices,
        default=Residency.OPTIONAL,
        help_text="Controls whether the 5-day Nairobi/Embu practical block ($100 USD lunch & tea) is none, optional, or required.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_course"
        ordering = ["level", "title"]
        verbose_name = "course"
        verbose_name_plural = "courses"

    def __str__(self) -> str:
        return f"{self.title} ({self.get_level_display()})"


class Price(models.Model):
    """
    Explicit course tuition per audience tier (local vs. international).
    Money is stored strictly as integer minor units (e.g., cents) plus ISO currency code.
    """

    class Audience(models.TextChoices):
        LOCAL = "local", "Local (Kenya)"
        INTERNATIONAL = "international", "International"

    class Currency(models.TextChoices):
        KES = "KES", "Kenyan Shilling (KES)"
        USD = "USD", "US Dollar (USD)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        db_index=True,
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
    )
    amount_minor = models.PositiveBigIntegerField(
        help_text="Tuition in minor currency units (e.g., KES 35,000 = 3500000; USD 1,800 = 180000).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_price"
        ordering = ["audience"]
        verbose_name = "price"
        verbose_name_plural = "prices"
        constraints = [
            models.UniqueConstraint(
                fields=["course", "audience"],
                name="unique_course_audience_price",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.amount_minor <= 0:
            raise ValidationError({"amount_minor": "Price amount_minor must be greater than zero."})

    @property
    def amount_major(self) -> Decimal:
        """Exact Decimal representation in major units (amount_minor / 100)."""
        return (Decimal(self.amount_minor) / Decimal(100)).quantize(Decimal("0.01"))

    def __str__(self) -> str:
        return f"{self.course.title} — {self.get_audience_display()}: {self.currency} {self.amount_major:,.2f}"


class Cohort(models.Model):
    """
    Scheduled intake cohort for a Course with capacity and enrollment gate.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="cohorts",
    )
    name = models.CharField(
        max_length=120,
        help_text="Cohort label, e.g., 'January 2027 Intake'.",
    )
    starts_on = models.DateField(db_index=True)
    capacity = models.PositiveIntegerField(default=30)
    enrollment_open = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether students can currently create new enrollments for this cohort.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_cohort"
        ordering = ["starts_on", "name"]
        verbose_name = "cohort"
        verbose_name_plural = "cohorts"

    def clean(self) -> None:
        super().clean()
        if self.capacity <= 0:
            raise ValidationError({"capacity": "Cohort capacity must be at least 1."})

    def __str__(self) -> str:
        status_label = "Open" if self.enrollment_open else "Closed"
        return f"{self.course.title} — {self.name} (Starts {self.starts_on}, {status_label})"