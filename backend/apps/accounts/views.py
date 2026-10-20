"""
Authentication & Session API Views for Eden Training Institute and Therapy (EdenLMS):
- CSRF cookie bootstrap (`GET /api/auth/csrf/`) + runtime `turnstile_site_key`
- Student Registration with Turnstile & Profile creation (`POST /api/auth/register/`)
- Session Login integrated with django-axes (`POST /api/auth/login/`)
- Session Logout (`POST /api/auth/logout/`)
- Current Authenticated User & Profile (`GET /api/auth/me/`)
"""
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserReadSerializer,
)
from .turnstile import verify_turnstile_token


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    """
    GET /api/auth/csrf/
    Sets the `csrftoken` cookie and returns the token value alongside the public
    Cloudflare Turnstile Site Key so the SPA can initialize bot protection at runtime.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        token = get_token(request)
        return Response(
            {
                "csrfToken": token,
                "turnstile_site_key": getattr(
                    settings, "TURNSTILE_SITE_KEY", "1x00000000000000000000AA"
                ),
            },
            status=status.HTTP_200_OK,
        )


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Validates Cloudflare Turnstile token, creates User + Profile, and opens an authenticated session.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        turnstile_token = serializer.validated_data.get("turnstile_token", "")
        remote_ip = request.META.get("REMOTE_ADDR")

        if not verify_turnstile_token(turnstile_token, remote_ip=remote_ip):
            return Response(
                {
                    "detail": "Bot verification failed. Please complete the security challenge."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        login(
            request._request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        return Response(
            UserReadSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/auth/login/
    Authenticates via Django + django-axes (locks out after 5 failed attempts).
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(
            request=request._request,
            username=email,
            password=password,
        )
        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account has been deactivated."},
                status=status.HTTP_403_FORBIDDEN,
            )

        login(request._request, user)
        return Response(
            UserReadSerializer(user).data,
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Terminates the current session and clears session state.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        logout(request._request)
        return Response(
            {"detail": "Signed out successfully."},
            status=status.HTTP_200_OK,
        )


class CurrentUserView(APIView):
    """
    GET /api/auth/me/
    Returns the authenticated user and profile, or `null` if anonymous (200 OK).
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        if not request.user or not request.user.is_authenticated:
            return Response({"user": None}, status=status.HTTP_200_OK)
        return Response(
            {"user": UserReadSerializer(request.user).data},
            status=status.HTTP_200_OK,
        )