"""
Explicit, tamper-resistant DRF serializers for Student Registration, Session Login,
Email Verification, Password Reset, and Current User ('me') profile inspection.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from .models import Profile, validate_iana_timezone
from .turnstile import verify_turnstile_token

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    """Read/update serializer for student Profile; effective_audience is strictly server-computed."""

    effective_audience = serializers.CharField(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "display_name",
            "country",
            "timezone",
            "effective_audience",
        )
        read_only_fields = ("effective_audience",)

    def validate_country(self, value: str) -> str:
        cleaned = value.strip().upper()
        if len(cleaned) != 2 or not cleaned.isalpha():
            raise serializers.ValidationError(
                "Country must be a 2-letter ISO 3166-1 alpha-2 code (e.g., KE, US, GB)."
            )
        return cleaned


class UserMeSerializer(serializers.ModelSerializer):
    """Trimmed serializer for the authenticated student ('/api/auth/me/')."""

    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "email_verified",
            "is_staff",
            "profile",
            "created_at",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    """
    Validates new student registration, Cloudflare Turnstile token, Argon2 password strength,
    and creates both User and Profile atomically.
    """

    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, min_length=10, max_length=128)
    display_name = serializers.CharField(max_length=150)
    country = serializers.CharField(max_length=2, default="KE")
    timezone = serializers.CharField(max_length=64, default="Africa/Nairobi")
    turnstile_token = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return normalized

    def validate_country(self, value: str) -> str:
        cleaned = value.strip().upper()
        if len(cleaned) != 2 or not cleaned.isalpha():
            raise serializers.ValidationError(
                "Country must be a 2-letter ISO code (e.g., KE, US, GB)."
            )
        return cleaned

    def validate_timezone(self, value: str) -> str:
        cleaned = value.strip()
        validate_iana_timezone(cleaned)
        return cleaned

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate_turnstile_token(self, value: str) -> str:
        request = self.context.get("request")
        remote_ip = request.META.get("REMOTE_ADDR") if request else None
        if not verify_turnstile_token(value, remote_ip=remote_ip):
            raise serializers.ValidationError(
                "Bot protection verification failed. Please complete the challenge and try again."
            )
        return value

    @transaction.atomic
    def create(self, validated_data: dict):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )
        Profile.objects.create(
            user=user,
            display_name=validated_data["display_name"].strip(),
            country=validated_data["country"],
            timezone=validated_data["timezone"],
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Validates login credentials and server-side Cloudflare Turnstile token."""

    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128)
    turnstile_token = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_turnstile_token(self, value: str) -> str:
        request = self.context.get("request")
        remote_ip = request.META.get("REMOTE_ADDR") if request else None
        if not verify_turnstile_token(value, remote_ip=remote_ip):
            raise serializers.ValidationError(
                "Bot protection verification failed. Please complete the challenge and try again."
            )
        return value


class EmailVerificationSerializer(serializers.Serializer):
    """Verifies a single-use uid + token email verification payload."""

    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs: dict) -> dict:
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as exc:
            raise serializers.ValidationError(
                {"token": "Invalid or expired email verification link."}
            ) from exc

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                {"token": "Invalid or expired email verification link."}
            )

        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Validates password reset request and Turnstile token.
    Never reveals whether the email exists in the database (Pre-Deployment Checklist #27).
    """

    email = serializers.EmailField(max_length=254)
    turnstile_token = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_turnstile_token(self, value: str) -> str:
        request = self.context.get("request")
        remote_ip = request.META.get("REMOTE_ADDR") if request else None
        if not verify_turnstile_token(value, remote_ip=remote_ip):
            raise serializers.ValidationError(
                "Bot protection verification failed. Please complete the challenge and try again."
            )
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Validates single-use password reset token and enforces Django password validators."""

    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=10, max_length=128)

    def validate(self, attrs: dict) -> dict:
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as exc:
            raise serializers.ValidationError(
                {"token": "Invalid or expired password reset link."}
            ) from exc

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                {"token": "Invalid or expired password reset link."}
            )

        validate_password(attrs["new_password"], user=user)
        attrs["user"] = user
        return attrs