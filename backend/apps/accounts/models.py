"""
Custom User and Student/Instructor Profile models for Dr. Violet's LMS (EdenLMS).
Implements UUID primary keys and email-based authentication before initial migrations.
"""
import uuid
from zoneinfo import available_timezones

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models


def validate_iana_timezone(value: str) -> None:
    """Validate that the provided timezone string is a valid IANA timezone."""
    if value not in available_timezones():
        raise ValidationError(f"'{value}' is not a valid IANA timezone identifier.")


class UserManager(BaseUserManager):
    """Custom manager for User where email is the unique authentication identifier."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("An email address must be provided.")
        normalized_email = self.normalize_email(email).strip().lower()
        user = self.model(email=normalized_email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model using UUID primary key and email as the login field.
    Username column is removed to prevent duplicate identity vectors.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField("email address", unique=True, db_index=True)
    email_verified = models.BooleanField(
        default=False,
        help_text="Designates whether the user has verified their email address.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email


class Profile(models.Model):
    """
    Extended profile storing student/instructor display name, ISO country code,
    manual audience override (for local vs. international tuition rules), and IANA timezone.
    """

    class AudienceOverride(models.TextChoices):
        AUTO = "auto", "Auto (Derived from Country)"
        LOCAL = "local", "Local (KES)"
        INTERNATIONAL = "international", "International (USD)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=150, blank=True)
    country = models.CharField(
        max_length=2,
        default="KE",
        help_text="ISO 3166-1 alpha-2 country code (e.g., KE, US, GB).",
    )
    timezone = models.CharField(
        max_length=64,
        default="Africa/Nairobi",
        validators=[validate_iana_timezone],
        help_text="IANA timezone string for rendering UTC live session schedules locally.",
    )
    audience_override = models.CharField(
        max_length=16,
        choices=AudienceOverride.choices,
        default=AudienceOverride.AUTO,
        help_text="Staff override for local vs. international pricing classification.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_profile"
        verbose_name = "profile"
        verbose_name_plural = "profiles"

    def __str__(self) -> str:
        return f"{self.display_name or self.user.email} ({self.country})"

    @property
    def effective_audience(self) -> str:
        """
        Compute student pricing audience strictly on the server:
        Uses staff override if set; otherwise 'local' for Kenya ('KE') and 'international' for all others.
        """
        if self.audience_override in (
            self.AudienceOverride.LOCAL,
            self.AudienceOverride.INTERNATIONAL,
        ):
            return self.audience_override
        return (
            self.AudienceOverride.LOCAL
            if self.country.upper() == "KE"
            else self.AudienceOverride.INTERNATIONAL
        )
