"""
Idempotent management command to seed Dr. Violet's real psychology programmes,
local (KES) and international (USD) integer minor-unit prices, intake cohorts,
classroom modules, signed video lessons, and live Google Meet sessions.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Cohort, Course, Price
from apps.classroom.models import Lesson, LiveSession, Module


class Command(BaseCommand):
    help = "Seed Dr. Violet's psychology Certificate and Diploma programmes and classroom lessons."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        programmes = [
            {
                "slug": "certificate-counselling-psychology",
                "title": "Certificate in Counselling Psychology",
                "level": Course.Level.CERTIFICATE,
                "residency": Course.Residency.OPTIONAL,
                "summary": (
                    "Foundational therapeutic ethics, active listening, trauma-informed "
                    "intake, and supervised case formulations delivered through weekly live lectures."
                ),
                "description": (
                    "Module 1: Therapeutic Ethics, Confidentiality & Intake Interviewing (Weeks 1-3)\n"
                    "Module 2: Person-Centred & Cognitive Behavioural Counselling Modalities (Weeks 4-6)\n"
                    "Module 3: Trauma-Informed Care, Crisis Intervention & Case Formulation (Weeks 7-10)\n"
                    "Module 4: Supervised Practicum & Optional 5-Day Nairobi/Embu Residency Block (Weeks 11-12)"
                ),
                "kes_minor": 3_500_000,
                "usd_minor": 55_000,
                "cohort_name": "January 2027 Intake",
                "starts_on": date(2027, 1, 15),
                "capacity": 30,
            },
            {
                "slug": "diploma-clinical-applied-psychology",
                "title": "Diploma in Clinical & Applied Psychology",
                "level": Course.Level.DIPLOMA,
                "residency": Course.Residency.REQUIRED,
                "summary": (
                    "Comprehensive psychometric assessment, psychopathology, group therapy "
                    "leadership, and mandatory 5-day in-person clinical practicum in Nairobi or Embu."
                ),
                "description": (
                    "Module 1: Advanced Psychopathology & Diagnostic Classification Systems (Weeks 1-6)\n"
                    "Module 2: Psychometric Testing, Clinical Formulation & Treatment Planning (Weeks 7-12)\n"
                    "Module 3: Group Therapy Leadership, Family Systems & Community Mental Health (Weeks 13-18)\n"
                    "Module 4: Mandatory 5-Day Practical Residency Block in Nairobi or Embu & Capstone (Weeks 19-24)"
                ),
                "kes_minor": 18_000_000,
                "usd_minor": 180_000,
                "cohort_name": "February 2027 Intake",
                "starts_on": date(2027, 2, 1),
                "capacity": 25,
            },
            {
                "slug": "certificate-child-adolescent-development",
                "title": "Certificate in Child & Adolescent Psychological Practice",
                "level": Course.Level.CERTIFICATE,
                "residency": Course.Residency.NONE,
                "summary": (
                    "Developmental milestones, school-based behavioural interventions, and "
                    "family systems guidance tailored for 100% online local and international learners."
                ),
                "description": (
                    "Module 1: Neurodevelopmental Stages across Infancy, Childhood & Adolescence (Weeks 1-3)\n"
                    "Module 2: School-Based Assessment & Behavioural Intervention Protocols (Weeks 4-6)\n"
                    "Module 3: Parent Consultation, Safeguarding & Cross-Cultural Ethics (Weeks 7-10)\n"
                    "Module 4: Remote Clinical Case Supervision via Live Google Meet Seminars (Weeks 11-12)"
                ),
                "kes_minor": 4_500_000,
                "usd_minor": 75_000,
                "cohort_name": "March 2027 Intake",
                "starts_on": date(2027, 3, 1),
                "capacity": 30,
            },
        ]

        now_utc = timezone.now()

        for item in programmes:
            course, _ = Course.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "level": item["level"],
                    "residency": item["residency"],
                    "summary": item["summary"],
                    "description": item["description"],
                    "status": Course.Status.PUBLISHED,
                },
            )
            Price.objects.update_or_create(
                course=course,
                audience=Price.Audience.LOCAL,
                defaults={
                    "currency": Price.Currency.KES,
                    "amount_minor": item["kes_minor"],
                },
            )
            Price.objects.update_or_create(
                course=course,
                audience=Price.Audience.INTERNATIONAL,
                defaults={
                    "currency": Price.Currency.USD,
                    "amount_minor": item["usd_minor"],
                },
            )
            cohort, _ = Cohort.objects.update_or_create(
                course=course,
                name=item["cohort_name"],
                defaults={
                    "starts_on": item["starts_on"],
                    "capacity": item["capacity"],
                    "enrollment_open": True,
                },
            )

            mod1, _ = Module.objects.update_or_create(
                course=course,
                order=1,
                defaults={
                    "title": "Foundations of Clinical Ethics & Intake Formulation",
                    "description": "Core ethical principles, confidentiality, and clinical intake.",
                },
            )
            lesson1, _ = Lesson.objects.update_or_create(
                module=mod1,
                order=1,
                defaults={
                    "title": "Therapeutic Boundaries & Informed Consent",
                    "kind": Lesson.Kind.VIDEO,
                    "duration_seconds": 1800,
                    "video_asset_id": f"asset_{course.slug}_mod1_les1",
                    "reading_body": (
                        "1. Establish clear informed consent prior to clinical intake.\n"
                        "2. Document confidentiality limits and safeguarding protocols.\n"
                        "3. Prepare case formulation notes for Thursday's live seminar."
                    ),
                    "is_published": True,
                },
            )
            Lesson.objects.update_or_create(
                module=mod1,
                order=2,
                defaults={
                    "title": "Intake Interviewing & Case Formulation Protocol",
                    "kind": Lesson.Kind.READING,
                    "duration_seconds": 900,
                    "video_asset_id": "",
                    "reading_body": (
                        "Structured clinical intake guide covering presenting problem, "
                        "psychosocial history, and mental status examination."
                    ),
                    "is_published": True,
                },
            )

            LiveSession.objects.update_or_create(
                cohort=cohort,
                title="Live Clinical Supervision & Case Seminar #1",
                defaults={
                    "starts_at": now_utc + timedelta(minutes=10),
                    "duration_minutes": 90,
                    "meet_url": "https://meet.google.com/eden-psy-live",
                    "recording_lesson": lesson1,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {len(programmes)} published programmes with classroom modules & live sessions."
            )
        )