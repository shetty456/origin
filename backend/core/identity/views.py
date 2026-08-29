import logging
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from django.db.models import F
from .models import Identity, OTPRequest
from .serializers import (
    OTPRequestSerializer,
    OTPVerifySerializer,
    PhoneOTPRequestSerializer,
    PhoneOTPVerifySerializer,
    LinkEmailRequestSerializer,
    LinkEmailVerifySerializer,
    LinkPhoneRequestSerializer,
    LinkPhoneVerifySerializer,
    MessageSerializer,
    TokenSerializer,
)

logger = logging.getLogger(__name__)

User = get_user_model()


def _issue_tokens(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


def _verify_otp(identity, otp_value):
    """
    Validate and atomically consume the OTP for an identity.
    Returns (otp_request, None) on success or (None, Response) on failure.

    The verified_at is set here via a conditional atomic update so that two
    concurrent requests with the correct OTP cannot both succeed (replay guard).
    """
    otp_request = OTPRequest.objects.get_latest_usable(identity)

    if not otp_request or not otp_request.is_usable:
        return None, Response(
            {"detail": "OTP has expired or is no longer valid. Please request a new one."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not otp_request.check_otp(otp_value):
        # Atomic DB-level increment — prevents parallel requests from bypassing
        # the attempt limit via a read-modify-write race condition.
        OTPRequest.objects.filter(pk=otp_request.pk).update(attempts=F("attempts") + 1)
        return None, Response(
            {"detail": "Invalid OTP."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()
    rows_updated = OTPRequest.objects.filter(
        pk=otp_request.pk, verified_at__isnull=True
    ).update(verified_at=now)
    if not rows_updated:
        # A concurrent request already consumed this OTP.
        return None, Response(
            {"detail": "OTP already used. Please request a new one."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    otp_request.verified_at = now
    return otp_request, None


# ---------------------------------------------------------------------------
# Signup / Login — public endpoints
# ---------------------------------------------------------------------------

class OTPRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        request=OTPRequestSerializer,
        responses={
            200: MessageSerializer,
            400: OpenApiResponse(description="Validation error."),
            429: OpenApiResponse(description="OTP requested too recently — wait before retrying."),
        },
        summary="Request Email OTP",
        description="Send a one-time password to the given email. Creates the user if they do not exist.",
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()

        identity, _ = Identity.objects.get_or_create_for_email(email)

        if OTPRequest.objects.is_on_cooldown(identity):
            return Response(
                {"detail": "Please wait before requesting another OTP."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        _, otp = OTPRequest.objects.create_for(identity)
        logger.info("OTP for %s: %s", email, otp)
        return Response({"detail": "OTP sent."}, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        request=OTPVerifySerializer,
        responses={
            200: TokenSerializer,
            400: OpenApiResponse(description="Invalid or expired OTP."),
        },
        summary="Verify Email OTP",
        description="Verify the OTP and receive JWT access and refresh tokens.",
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        otp = serializer.validated_data["otp"]

        try:
            identity = Identity.objects.get_by_provider(Identity.PROVIDER_EMAIL, email)
        except Identity.DoesNotExist:
            return Response(
                {"detail": "Invalid email or OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_request, error = _verify_otp(identity, otp)
        if error:
            return error

        if not identity.verified_at:
            identity.verified_at = otp_request.verified_at
            identity.save(update_fields=["verified_at", "updated_at"])

        return Response(_issue_tokens(identity.user), status=status.HTTP_200_OK)


class PhoneOTPRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        request=PhoneOTPRequestSerializer,
        responses={
            200: MessageSerializer,
            400: OpenApiResponse(description="Validation error."),
            429: OpenApiResponse(description="OTP requested too recently — wait before retrying."),
        },
        summary="Request Phone OTP",
        description="Send a one-time password to the given phone number. Creates the user if they do not exist.",
    )
    def post(self, request):
        serializer = PhoneOTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]

        identity, _ = Identity.objects.get_or_create_for_phone(phone)

        if OTPRequest.objects.is_on_cooldown(identity):
            return Response(
                {"detail": "Please wait before requesting another OTP."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        _, otp = OTPRequest.objects.create_for(identity)
        logger.info("Phone OTP for %s: %s", phone, otp)
        return Response({"detail": "OTP sent."}, status=status.HTTP_200_OK)


class PhoneOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        request=PhoneOTPVerifySerializer,
        responses={
            200: TokenSerializer,
            400: OpenApiResponse(description="Invalid or expired OTP."),
        },
        summary="Verify Phone OTP",
        description="Verify the phone OTP and receive JWT access and refresh tokens.",
    )
    def post(self, request):
        serializer = PhoneOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        otp = serializer.validated_data["otp"]

        try:
            identity = Identity.objects.get_by_provider(Identity.PROVIDER_PHONE, phone)
        except Identity.DoesNotExist:
            return Response(
                {"detail": "Invalid phone number or OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp_request, error = _verify_otp(identity, otp)
        if error:
            return error

        if not identity.verified_at:
            identity.verified_at = otp_request.verified_at
            identity.save(update_fields=["verified_at", "updated_at"])

        return Response(_issue_tokens(identity.user), status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Identity linking — authenticated endpoints
# Lets an already-logged-in user add a second identity to their account.
# ---------------------------------------------------------------------------

def _link_request(request, provider, identifier, log_label):
    try:
        identity, _ = Identity.objects.get_or_create_for_link(
            user=request.user,
            provider=provider,
            identifier=identifier,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    if identity.is_verified:
        return Response(
            {"detail": f"This {provider} is already verified on your account."},
            status=status.HTTP_409_CONFLICT,
        )

    if OTPRequest.objects.is_on_cooldown(identity):
        return Response(
            {"detail": "Please wait before requesting another OTP."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    _, otp = OTPRequest.objects.create_for(identity)
    logger.info("Link OTP (%s) for %s: %s", provider, log_label, otp)
    return Response({"detail": "OTP sent."}, status=status.HTTP_200_OK)


def _link_verify(request, provider, identifier, otp_value):
    try:
        identity = Identity.objects.get_by_provider(provider, identifier)
    except Identity.DoesNotExist:
        return Response(
            {"detail": "No pending link found. Request an OTP first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if identity.user_id != request.user.pk:
        return Response({"detail": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST)

    otp_request, error = _verify_otp(identity, otp_value)
    if error:
        return error

    identity.verified_at = otp_request.verified_at
    identity.save(update_fields=["verified_at", "updated_at"])

    return Response(
        {"detail": f"{provider.capitalize()} linked successfully."},
        status=status.HTTP_200_OK,
    )


class LinkEmailRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Identity"],
        request=LinkEmailRequestSerializer,
        responses={
            200: MessageSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            409: OpenApiResponse(description="Email already linked to an account."),
            429: OpenApiResponse(description="OTP requested too recently — wait before retrying."),
        },
        summary="Link email to account",
        description="Send an OTP to the given email to link it to the authenticated user's account.",
    )
    def post(self, request):
        serializer = LinkEmailRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        return _link_request(request, Identity.PROVIDER_EMAIL, email, email)


class LinkEmailVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Identity"],
        request=LinkEmailVerifySerializer,
        responses={
            200: MessageSerializer,
            400: OpenApiResponse(description="Invalid or expired OTP."),
            401: OpenApiResponse(description="Authentication required."),
        },
        summary="Verify email link OTP",
        description="Verify the OTP and link the email to the authenticated user's account.",
    )
    def post(self, request):
        serializer = LinkEmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        otp = serializer.validated_data["otp"]
        return _link_verify(request, Identity.PROVIDER_EMAIL, email, otp)


class LinkPhoneRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Identity"],
        request=LinkPhoneRequestSerializer,
        responses={
            200: MessageSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            409: OpenApiResponse(description="Phone already linked to an account."),
            429: OpenApiResponse(description="OTP requested too recently — wait before retrying."),
        },
        summary="Link phone to account",
        description="Send an OTP to the given phone to link it to the authenticated user's account.",
    )
    def post(self, request):
        serializer = LinkPhoneRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        return _link_request(request, Identity.PROVIDER_PHONE, phone, phone)


class LinkPhoneVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Identity"],
        request=LinkPhoneVerifySerializer,
        responses={
            200: MessageSerializer,
            400: OpenApiResponse(description="Invalid or expired OTP."),
            401: OpenApiResponse(description="Authentication required."),
        },
        summary="Verify phone link OTP",
        description="Verify the OTP and link the phone to the authenticated user's account.",
    )
    def post(self, request):
        serializer = LinkPhoneVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data["phone"]
        otp = serializer.validated_data["otp"]
        return _link_verify(request, Identity.PROVIDER_PHONE, phone, otp)
