"""
Transactional Residency Booking, DPO Fee Initiation, and Course Completion Gate Services.
Complies with Blueprint Phase 5:
- Locks ResidencyBlock with `select_for_update()` and assigns a unique `seat_number` (1..capacity)
  inside `transaction.atomic()` so concurrent requests for the last seat never overbook.
- Creates a USD 100 (`amount_minor = 10000`) DPO Payment through the Phase 3 payment flow.
- Enforces `Course.residency == 'required'` before allowing course completion.
"""
import uuid

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalog.models import Course
from apps.classroom.models import Lesson, LessonProgress
from apps.enrollments.models import Enrollment
from apps.payments.models import Payment
from apps.payments.services import request_dpo_trans_token

from .models import ResidencyBlock, ResidencyRegistration


def book_residency_block(
    *,
    user,
    block_id,
    dietary_notes: str = "",
    redirect_url: str = "http://localhost:5173/my-learning?residency_return=1",
    back_url: str = "http://localhost:5173/my-learning",
) -> ResidencyRegistration:
    """
    Atomically reserve a seat in a 5-day Nairobi or Embu ResidencyBlock and initiate its
    $100 USD DPO Payment.
    Guaranteed against overbooking under concurrent requests via `select_for_update()` AND
    the database-level `unique_active_block_seat_number` constraint.
    """
    try:
        with transaction.atomic():
            locked_block = (
                ResidencyBlock.objects.select_for_update()
                .select_related("course")
                .get(pk=block_id)
            )

            if not locked_block.is_open:
                raise ValidationError("This residency block is closed for registration.")

            if locked_block.course.residency == Course.Residency.NONE:
                raise ValidationError("This course is 100% online and does not include a residency block.")

            enrollment = (
                Enrollment.objects.for_user(user)
                .select_for_update()
                .filter(
                    cohort__course=locked_block.course,
                    status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED],
                )
                .first()
            )
            if enrollment is None:
                raise ValidationError(
                    "An active, paid course enrollment is required before booking a residency block."
                )

            existing = ResidencyRegistration.objects.filter(
                enrollment=enrollment,
                block=locked_block,
            ).first()
            if existing is not None and existing.status != ResidencyRegistration.Status.CANCELLED:
                raise ValidationError("You are already registered for this residency block.")

            occupied_seats = set(
                ResidencyRegistration.objects.select_for_update()
                .filter(
                    block=locked_block,
                    status__in=[
                        ResidencyRegistration.Status.PENDING_PAYMENT,
                        ResidencyRegistration.Status.CONFIRMED,
                    ],
                )
                .values_list("seat_number", flat=True)
            )

            if len(occupied_seats) >= locked_block.capacity:
                raise ValidationError("This residency block has reached full capacity.")

            allocated_seat = next(
                seat
                for seat in range(1, locked_block.capacity + 1)
                if seat not in occupied_seats
            )

            company_ref = f"RES-{uuid.uuid4().hex[:12].upper()}"
            placeholder_ref = f"PENDING-{company_ref}"

            payment = Payment.objects.create(
                enrollment=enrollment,
                provider=Payment.Provider.DPO,
                provider_ref=placeholder_ref,
                company_ref=company_ref,
                amount_minor=locked_block.fee_minor,
                currency=locked_block.currency,
                status=Payment.Status.INITIATED,
            )

            trans_token, checkout_url, create_log = request_dpo_trans_token(
                payment=payment,
                redirect_url=redirect_url,
                back_url=back_url,
            )
            payment.provider_ref = trans_token
            payment.checkout_url = checkout_url
            payment.raw_log = {
                "purpose": "residency_block_fee",
                "block_id": str(locked_block.id),
                "location": locked_block.location,
                "initiation": create_log,
                "verifications": [],
            }
            payment.save(
                update_fields=["provider_ref", "checkout_url", "raw_log", "updated_at"]
            )

            registration = ResidencyRegistration.objects.create(
                enrollment=enrollment,
                block=locked_block,
                seat_number=allocated_seat,
                status=ResidencyRegistration.Status.PENDING_PAYMENT,
                payment=payment,
                dietary_notes=dietary_notes.strip(),
            )
            return registration
    except IntegrityError as exc:
        raise ValidationError(
            "This residency block has reached full capacity or was concurrently booked."
        ) from exc


@transaction.atomic
def check_and_complete_course_enrollment(enrollment: Enrollment) -> Enrollment:
    """
    Evaluate whether an ACTIVE Enrollment has satisfied all requirements for `status = COMPLETED`:
    1. All published lessons in the course are marked `COMPLETED` by the student.
    2. If `course.residency == Course.Residency.REQUIRED`, the student MUST hold a `CONFIRMED`
       `ResidencyRegistration` for that course (Blueprint Phase 5).
    """
    locked = (
        Enrollment.objects.select_for_update()
        .select_related("cohort__course")
        .get(pk=enrollment.pk)
    )
    if locked.status == Enrollment.Status.COMPLETED:
        return locked

    if locked.status != Enrollment.Status.ACTIVE:
        raise ValidationError("Only an active enrollment can be marked completed.")

    course = locked.cohort.course
    published_lesson_ids = list(
        Lesson.objects.filter(
            module__course=course,
            is_published=True,
        ).values_list("id", flat=True)
    )

    if published_lesson_ids:
        completed_count = LessonProgress.objects.filter(
            user=locked.user,
            lesson_id__in=published_lesson_ids,
            status=LessonProgress.Status.COMPLETED,
        ).count()
        if completed_count < len(published_lesson_ids):
            raise ValidationError(
                f"Cannot complete course: {completed_count} of {len(published_lesson_ids)} lessons completed."
            )

    if course.residency == Course.Residency.REQUIRED:
        has_confirmed_residency = ResidencyRegistration.objects.filter(
            enrollment=locked,
            status=ResidencyRegistration.Status.CONFIRMED,
        ).exists()
        if not has_confirmed_residency:
            raise ValidationError(
                "This course requires a confirmed 5-day practical residency block in Nairobi or Embu before completion."
            )

    locked.status = Enrollment.Status.COMPLETED
    locked.completed_at = timezone.now()
    locked.save(update_fields=["status", "completed_at", "updated_at"])
    return locked