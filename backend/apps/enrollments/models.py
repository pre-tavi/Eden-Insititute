"""
Enrollment state machine and row-isolated queryset manager for Dr. Violet's LMS (EdenLMS).
Complies with Blueprint Section 4 and Pre-Deployment Security Checklist #4, #7, and #8.
"""
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.catalog.models import Cohort, Price


class EnrollmentQuerySet(models.QuerySet):
    """Custom QuerySet enforcing per-student record isolation."""

    def for_user(self, user) -> "EnrollmentQuerySet":
        """
        Scope enrollment records strictly to the authenticated student.
        Returns an empty queryset for anonymous users.
        """
        if not user or not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(user=user)


class EnrollmentManager(models.Manager.from_queryset(EnrollmentQuerySet)):
    """Default manager exposing .for_user(request.user) on Enrollment.objects."""


class Enrollment(models.Model):
    """
    Links a student User to a Course Cohort with a controlled lifecycle state machine.
    New student enrollments always start in PENDING_PAYMENT.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending Payment"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        WITHDRAWN = "withdrawn", "Withdrawn"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.PROTECT,
        related_name="enrollments",
    )
    status = models.CharField(
        max_length=24,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    activated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    activation_source = models.CharField(
        max_length=64,
        blank=True,
        help_text="Audit trail recording how enrollment was activated (e.g., dpo_webhook, staff_manual).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EnrollmentManager()

    class Meta:
        db_table = "enrollments_enrollment"
        ordering = ["-created_at"]
        verbose_name = "enrollment"
        verbose_name_plural = "enrollments"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "cohort"],
                name="unique_student_cohort_enrollment",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} -> {self.cohort} [{self.status}]"

    def get_server_price(self) -> Price | None:
        """
        Resolve the authoritative Price record on the server from the student's Profile
        effective_audience ('local' -> KES, 'international' -> USD).
        Never trusts a price or audience sent by the browser.
        """
        audience = Price.Audience.LOCAL
        profile = getattr(self.user, "profile", None)
        if profile is not None:
            audience = profile.effective_audience

        price = self.cohort.course.prices.filter(audience=audience).first()
        if price is None:
            price = self.cohort.course.prices.first()
        return price


@transaction.atomic
def activate_enrollment(enrollment: Enrollment, *, source: str = "dpo_verified") -> Enrollment:
    """
    Single authoritative code path that transitions an Enrollment to status=ACTIVE.
    Called ONLY from a verified server-to-server DPO payment notification or an audited staff action.
    Idempotent: calling twice on an already ACTIVE enrollment is a safe no-op.
    """
    locked = Enrollment.objects.select_for_update().get(pk=enrollment.pk)
    if locked.status == Enrollment.Status.ACTIVE:
        return locked

    if locked.status in (Enrollment.Status.WITHDRAWN, Enrollment.Status.REFUNDED):
        raise ValidationError(
            f"Cannot activate an enrollment in '{locked.status}' state."
        )

    locked.status = Enrollment.Status.ACTIVE
    locked.activated_at = timezone.now()
    locked.activation_source = source
    locked.save(update_fields=["status", "activated_at", "activation_source", "updated_at"])
    return locked