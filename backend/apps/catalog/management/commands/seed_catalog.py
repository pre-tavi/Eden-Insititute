"""
Idempotent management command to seed Dr. Violet's real psychology programmes,
local (KES) and international (USD) integer minor-unit prices, and intake cohorts.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Cohort, Course, Price


class Command(BaseCommand):
    help = "Seed Dr. Violet's psychology Certificate and Diploma catalog programmes."

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
                "kes_minor": 3_500_000,  # KES 35,000.00
                "usd_minor": 55_000,     # USD 550.00
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
                "kes_minor": 18_000_000,  # KES 180,000.00
                "usd_minor": 180_000,     # USD 1,800.00 (~232,000 KES international tier)
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
                "kes_minor": 4_500_000,  # KES 45,000.00
                "usd_minor": 75_000,     # USD 750.00
                "cohort_name": "March 2027 Intake",
                "starts_on": date(2027, 3, 1),
                "capacity": 30,
            },
        ]

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
            Cohort.objects.update_or_create(
                course=course,
                name=item["cohort_name"],
                defaults={
                    "starts_on": item["starts_on"],
                    "capacity": item["capacity"],
                    "enrollment_open": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {len(programmes)} published psychology programmes."
            )
        )