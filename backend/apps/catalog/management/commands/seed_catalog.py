"""
Idempotent management command to seed Eden Training Institute and Therapy's official
TVETA-licensed and KNEC-examined psychology & marriage/family therapy programmes,
and deterministically configure Dr. Violet's superuser + 2FA token in Neon PostgreSQL.
"""
import os
from datetime import date, timedelta

from axes.models import AccessAttempt
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from apps.accounts.models import Profile
from apps.catalog.models import Cohort, Course, Price
from apps.classroom.models import Lesson, LiveSession, Module
from apps.residency.models import ResidencyBlock

User = get_user_model()

LEGACY_DEMO_SLUGS = (
    "diploma-clinical-applied-psychology",
    "certificate-child-adolescent-development",
)


class Command(BaseCommand):
    help = (
        "Seed Eden Training Institute and Therapy (TVETA/PRIVATE/TVC/0019/2016) "
        "catalog and ensure Dr. Violet's superuser + 2FA token are active."
    )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        # 1. Unconditionally sync Dr. Violet's Superuser credentials & clear any Axes lockouts
        admin_email = (
            os.environ.get("DJANGO_SUPERUSER_EMAIL", "dr.violet@edenlms.org")
            .strip()
            .lower()
        )
        admin_password = os.environ.get(
            "DJANGO_SUPERUSER_PASSWORD", "DrVioletAdmin!2026"
        ).strip()
        admin_otp_token = os.environ.get(
            "DJANGO_SUPERUSER_OTP_TOKEN", "EDEN-2026-OTP"
        ).strip()

        AccessAttempt.objects.all().delete()

        admin_user, _ = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "email_verified": True,
            },
        )
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_active = True
        admin_user.email_verified = True
        admin_user.set_password(admin_password)
        admin_user.save()

        Profile.objects.update_or_create(
            user=admin_user,
            defaults={
                "display_name": "Dr. Violet (Director)",
                "country": "KE",
                "timezone": "Africa/Nairobi",
            },
        )

        # Seed a pool of StaticToken entries so `EDEN-2026-OTP` works across multiple logins
        static_device, _ = StaticDevice.objects.get_or_create(
            user=admin_user,
            name="Dr. Violet Backup OTP",
            defaults={"confirmed": True},
        )
        static_device.confirmed = True
        static_device.save(update_fields=["confirmed"])
        existing_count = static_device.token_set.filter(token=admin_otp_token).count()
        for _ in range(max(0, 25 - existing_count)):
            StaticToken.objects.create(device=static_device, token=admin_otp_token)

        # 2. Clean up legacy placeholder courses without enrollments
        for old_slug in LEGACY_DEMO_SLUGS:
            old_course = Course.objects.filter(slug=old_slug).first()
            if old_course is not None and not old_course.cohorts.filter(
                enrollments__isnull=False
            ).exists():
                ResidencyBlock.objects.filter(course=old_course).delete()
                old_course.delete()

        # 3. Seed Official TVETA & KNEC Programmes
        programmes = [
            {
                "slug": "diploma-counseling-marriage-family-therapy-knec",
                "title": "Diploma in Counseling: Marriage and Family Therapy Option (KNEC)",
                "level": Course.Level.DIPLOMA,
                "residency": Course.Residency.REQUIRED,
                "summary": (
                    "TVETA-licensed (TVETA/PRIVATE/TVC/0019/2016) and KNEC-examined Diploma "
                    "in Marriage and Family Therapy. Capped at a maximum of 14 trainees per cohort "
                    "with weekly live supervision and a mandatory 5-day practical block at "
                    "Shepherds Building (Buruburu Phase II, Nairobi) or Embu."
                ),
                "description": (
                    "Module 1: Systemic Family Therapy Theories, Genograms & Marital Assessment (KNEC Unit 1)\n"
                    "Module 2: Couples Communication, Conflict Resolution & Attachment Repair (KNEC Unit 2)\n"
                    "Module 3: Trauma, Domestic Crisis Intervention & Legal/Ethical Practice in Kenya (KNEC Unit 3)\n"
                    "Module 4: Mandatory 5-Day Clinical Practicum (Shepherds Building, Buruburu Phase II Nairobi / Embu) & KNEC Research Project"
                ),
                "kes_minor": 15_000_000,
                "usd_minor": 180_000,
                "cohort_name": "January 2027 KNEC Intake (Max 14 Trainees)",
                "starts_on": date(2027, 1, 18),
                "capacity": 14,
                "mod1_title": "Systemic Family Therapy & Relational Intake Formulation",
                "mod1_desc": (
                    "Clinical mastery of systemic family interviewing, multi-generational genograms, "
                    "and ethical contracting under KNEC and TVETA standards."
                ),
                "lesson1_title": "Constructing Clinical Genograms & Systemic Hypotheses",
                "lesson1_asset": "eden_tveta_0019_mft_mod1_les1",
                "lesson1_notes": (
                    "1. Map three-generation relational patterns and triangles during the initial marriage/family intake.\n"
                    "2. Establish informed consent, confidentiality boundaries, and child safeguarding duties under Kenyan law.\n"
                    "3. Prepare your anonymised couple formulation for Dr. Violet's live Thursday supervision seminar."
                ),
                "lesson2_title": "KNEC Marriage & Family Therapy Ethics & Intake Protocol",
                "lesson2_notes": (
                    "Official Eden Training Institute and Therapy clinical intake protocol "
                    "(Shepherds Building, Buruburu Phase II, Mumias South Road, Nairobi). "
                    "Covers relational history, dyadic adjustment screening, and crisis safety planning."
                ),
                "live_title": "Live KNEC Clinical Supervision & Family Case Seminar #1",
            },
            {
                "slug": "certificate-counselling-psychology",
                "title": "Certificate in Counselling Psychology & Clinical Therapy Skills",
                "level": Course.Level.CERTIFICATE,
                "residency": Course.Residency.OPTIONAL,
                "summary": (
                    "Accredited foundational counseling skills, trauma-informed active listening, "
                    "grief support, and ethical case management delivered via live Google Meet lectures "
                    "with an optional 5-day practical block at Buruburu Phase II (Nairobi) or Embu."
                ),
                "description": (
                    "Module 1: Counseling Ethics, Boundaries & The Therapeutic Alliance (Weeks 1-3)\n"
                    "Module 2: Person-Centred, CBT & Solution-Focused Brief Therapy Skills (Weeks 4-6)\n"
                    "Module 3: Grief, Loss, Addiction & Community Mental Health First Aid (Weeks 7-10)\n"
                    "Module 4: Supervised Role-Play Practicum & Optional 5-Day Nairobi (Buruburu Phase II) / Embu Residency (Weeks 11-12)"
                ),
                "kes_minor": 3_500_000,
                "usd_minor": 55_000,
                "cohort_name": "February 2027 Intake (Max 14 Trainees)",
                "starts_on": date(2027, 2, 1),
                "capacity": 14,
                "mod1_title": "Foundations of Therapeutic Ethics & Active Listening",
                "mod1_desc": (
                    "Core counseling micro-skills, unconditional positive regard, and structured clinical intake."
                ),
                "lesson1_title": "Therapeutic Boundaries, Empathy & Informed Consent",
                "lesson1_asset": "eden_tveta_0019_cert_mod1_les1",
                "lesson1_notes": (
                    "1. Establish clear therapeutic boundaries and informed consent prior to client intake.\n"
                    "2. Practice reflective listening, paraphrasing, and somatic grounding.\n"
                    "3. Review case vignettes ahead of the live Google Meet supervision session."
                ),
                "lesson2_title": "Structured Client Intake & Mental Status Examination Guide",
                "lesson2_notes": (
                    "Step-by-step clinical intake template used at Eden Training Institute and Therapy "
                    "for documenting presenting concerns, psychosocial history, and risk assessment."
                ),
                "live_title": "Live Counseling Micro-Skills & Supervision Seminar #1",
            },
            {
                "slug": "certificate-marriage-family-therapy-foundations",
                "title": "Certificate in Marriage, Family & Adolescent Therapy Foundations",
                "level": Course.Level.CERTIFICATE,
                "residency": Course.Residency.NONE,
                "summary": (
                    "100% online certificate programme in pre-marital counseling, parenting systems, "
                    "and adolescent behavioral guidance designed for working professionals across Kenya "
                    "and international diaspora learners."
                ),
                "description": (
                    "Module 1: Pre-Marital Counseling & Marital Expectations Assessment (Weeks 1-3)\n"
                    "Module 2: Parenting Systems, Child Developmental Milestones & School Consultation (Weeks 4-6)\n"
                    "Module 3: Adolescent Identity, Digital Wellbeing & Family Communication (Weeks 7-10)\n"
                    "Module 4: Online Case Formulation & Live Google Meet Faculty Supervision (Weeks 11-12)"
                ),
                "kes_minor": 4_500_000,
                "usd_minor": 75_000,
                "cohort_name": "March 2027 Online Intake",
                "starts_on": date(2027, 3, 1),
                "capacity": 20,
                "mod1_title": "Pre-Marital Assessment & Family Systems Foundations",
                "mod1_desc": (
                    "Evidence-based frameworks for guiding couples, parents, and adolescents remotely."
                ),
                "lesson1_title": "Assessing Couple Dynamics & Family Communication Styles",
                "lesson1_asset": "eden_tveta_0019_online_mod1_les1",
                "lesson1_notes": (
                    "1. Administer structured pre-marital and family communication inventories.\n"
                    "2. Identify pursuer-distancer cycles and guide de-escalation exercises.\n"
                    "3. Complete the adolescent safeguarding checklist before Unit 2."
                ),
                "lesson2_title": "Adolescent & Family Safeguarding Protocol",
                "lesson2_notes": (
                    "Comprehensive clinical reading covering cross-cultural family systems, "
                    "adolescent assent, and tele-counseling ethics."
                ),
                "live_title": "Live Online Family & Adolescent Case Seminar #1",
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
                    "title": item["mod1_title"],
                    "description": item["mod1_desc"],
                },
            )
            lesson1, _ = Lesson.objects.update_or_create(
                module=mod1,
                order=1,
                defaults={
                    "title": item["lesson1_title"],
                    "kind": Lesson.Kind.VIDEO,
                    "duration_seconds": 1800,
                    "video_asset_id": item["lesson1_asset"],
                    "reading_body": item["lesson1_notes"],
                    "is_published": True,
                },
            )
            Lesson.objects.update_or_create(
                module=mod1,
                order=2,
                defaults={
                    "title": item["lesson2_title"],
                    "kind": Lesson.Kind.READING,
                    "duration_seconds": 900,
                    "video_asset_id": "",
                    "reading_body": item["lesson2_notes"],
                    "is_published": True,
                },
            )

            LiveSession.objects.update_or_create(
                cohort=cohort,
                title=item["live_title"],
                defaults={
                    "starts_at": now_utc + timedelta(minutes=10),
                    "duration_minutes": 90,
                    "meet_url": "https://meet.google.com/eden-therapy-live",
                    "recording_lesson": lesson1,
                },
            )

            if course.residency in (Course.Residency.OPTIONAL, Course.Residency.REQUIRED):
                ResidencyBlock.objects.update_or_create(
                    course=course,
                    location=ResidencyBlock.Location.NAIROBI,
                    starts_on=date(2027, 4, 12),
                    defaults={
                        "title": (
                            "Nairobi 5-Day Practical Block "
                            "(Shepherds Building, Buruburu Phase II, Mumias South Rd)"
                        ),
                        "ends_on": date(2027, 4, 16),
                        "capacity": 14,
                        "fee_minor": 10_000,
                        "currency": Price.Currency.USD,
                        "is_open": True,
                    },
                )
                ResidencyBlock.objects.update_or_create(
                    course=course,
                    location=ResidencyBlock.Location.EMBU,
                    starts_on=date(2027, 4, 19),
                    defaults={
                        "title": "Embu 5-Day Practical Clinical Residency Block",
                        "ends_on": date(2027, 4, 23),
                        "capacity": 14,
                        "fee_minor": 10_000,
                        "currency": Price.Currency.USD,
                        "is_open": True,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully seeded Eden Training Institute and Therapy (TVETA/PRIVATE/TVC/0019/2016) "
                f"catalog and synced superuser login ({admin_email})."
            )
        )
