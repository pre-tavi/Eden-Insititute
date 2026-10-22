"""
Session-authenticated API views for Student Registration, Login, Logout,
Email Verification, Password Reset, CSRF cookie priming, and 'me' profile lookup.
"""
import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import (
    EmailVerificationSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserMeSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    """
    GET /api/auth/csrf/
    Sets the csrftoken cookie and returns the token so the React SPA can attach X-CSRFToken.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"csrfToken": get_token(request)}, status=status.HTTP_200_OK)


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Creates a new student User + Profile, sends a verification email, and establishes a session.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Issue single-use email verification token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        send_mail(
            subject="Verify your Dr. Violet's LMS Student Account",
            message=(
                f"Welcome to Dr. Violet's Institute of Psychology.\n\n"
                f"Verify your email using UID: {uid} and Token: {token}"
            ),
            from_email="noreply@edenlms.org",
            recipient_list=[user.email],
            fail_silently=bool(getattr(settings, 'DEBUG', False)),
        )

        # Log the user in using the standard ModelBackend after creation
        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        return Response(
            UserMeSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/auth/login/
    Authenticates via django-axes + ModelBackend and issues an HttpOnly session cookie.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request=request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response(UserMeSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Invalidates the server-side session and clears the session cookie.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        logout(request)
        return Response({"detail": "Successfully signed out."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """
    GET /api/auth/me/
    Returns the authenticated user's profile and server-computed tuition audience.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(UserMeSerializer(request.user).data, status=status.HTTP_200_OK)


class EmailVerificationView(APIView):
    """
    POST /api/auth/verify-email/
    Verifies a student's email address using a single-use uid + token pair.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified", "updated_at"])

        return Response(
            {"detail": "Email address verified successfully.", "email_verified": True},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/
    Sends a single-use password reset token if the email exists; returns an identical response
    either way to prevent account enumeration (Pre-Deployment Checklist #27).
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_mail(
                subject="Password Reset — Dr. Violet's LMS",
                message=(
                    f"A password reset was requested for your account.\n\n"
                    f"Use UID: {uid} and Token: {token} to set a new password."
                ),
                from_email="noreply@edenlms.org",
                recipient_list=[user.email],
                fail_silently=bool(getattr(settings, 'DEBUG', False)),
            )

        return Response(
            {
                "detail": (
                    "If an account exists for that email address, "
                    "password reset instructions have been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/auth/password-reset/confirm/
    Resets the user's password with Argon2 hashing and invalidates the single-use token.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        new_password = serializer.validated_data["new_password"]

        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])

        return Response(
            {"detail": "Password has been reset successfully. You may now sign in."},
            status=status.HTTP_200_OK,
        )