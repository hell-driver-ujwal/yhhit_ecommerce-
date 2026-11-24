from collections.abc import Mapping

from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView

from .serializers import EmailLoginSerializer, ProfileSerializer, RegistrationSerializer


REFRESH_COOKIE = "accounts_refresh"


def account_cookie_path():
    return reverse("accounts:login").removesuffix("login/")


class LoggedOutOnly(BasePermission):
    message = "Log out before registering or logging in again."

    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return False
        cookie = request.COOKIES.get(REFRESH_COOKIE)
        if cookie:
            try:
                RefreshToken(cookie)
            except TokenError:
                return True
            raise PermissionDenied(self.message)
        return True


def protect_browser_post(request):
    # Browser forms and fetch requests identify their origin. DRF's browsable
    # forms include the CSRF token, and same-origin JS can send X-CSRFToken.
    if any(header in request.headers for header in ("Origin", "Referer", "Sec-Fetch-Site")):
        SessionAuthentication().enforce_csrf(request)


@extend_schema(auth=[], description="Register a buyer or seller while logged out. Password confirmation is required.")
class RegistrationView(generics.CreateAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (LoggedOutOnly,)
    serializer_class = RegistrationSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
@extend_schema(
    auth=[], description="Log in while signed out. Browser requests require a CSRF token.",
    request=inline_serializer("EmailCredentials", fields={"email": serializers.EmailField(), "password": serializers.CharField()}),
    responses=inline_serializer("JwtPair", fields={"access": serializers.CharField(), "refresh": serializers.CharField()}),
)
class LoginView(TokenObtainPairView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (LoggedOutOnly,)
    serializer_class = EmailLoginSerializer

    def post(self, request, *args, **kwargs):
        protect_browser_post(request)
        response = super().post(request, *args, **kwargs)
        response.set_cookie(
            REFRESH_COOKIE, response.data["refresh"],
            max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
            path=account_cookie_path(),
            httponly=True, secure=request.is_secure() or not settings.DEBUG, samesite="Strict",
        )
        return response


@extend_schema(
    description="Revoke the refresh token. With the login cookie, send an empty object or an empty body.",
    request=inline_serializer("LogoutInput", fields={"refresh": serializers.CharField(required=False)}),
    responses={200: {"type": "object", "additionalProperties": False}},
)
class LogoutView(TokenBlacklistView):
    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if "data" not in kwargs and self.request.COOKIES.get(REFRESH_COOKIE):
            # The signed-in browser already supplies the token with its POST.
            del serializer.fields["refresh"]
        return serializer

    def post(self, request, *args, **kwargs):
        protect_browser_post(request)
        cookie = request.COOKIES.get(REFRESH_COOKIE)
        if not isinstance(request.data, Mapping):
            raise ValidationError({"detail": "Expected a JSON object."})
        submitted = request.data.get("refresh")
        if cookie and submitted and submitted != cookie:
            raise ValidationError({"refresh": "The token differs from this client's login."})
        data = {"refresh": cookie} if cookie and not submitted else request.data
        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc
        response = Response(serializer.validated_data)
        response.delete_cookie(REFRESH_COOKIE, path=account_cookie_path(), samesite="Strict")
        return response


class ProfileView(generics.RetrieveUpdateAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = ProfileSerializer
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return self.request.user
