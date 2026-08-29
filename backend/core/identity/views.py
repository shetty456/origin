import logging
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from core.users.models import User
from .models import Identity, OTPRequest
from .serializers import OTPRequestSerializer, OTPVerifySerializer

logger = logging.getLogger(__name__)


def _issue_tokens(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class OTPRequestView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OTPRequestSerializer,
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
        summary="Request OTP",
        description="Send a one-time password to the given email address. Creates the user account if it does not exist.",
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()

        # Find or create the Identity + User
        try:
            identity = Identity.objects.get(provider=Identity.PROVIDER_EMAIL, identifier=email)
        except Identity.DoesNotExist:
            user = User.objects.create_user(email=email)
            identity = Identity.objects.create(
                user=user,
                provider=Identity.PROVIDER_EMAIL,
                identifier=email,
            )

        # Resend cooldown — one OTP per 60 seconds
        cooldown_cutoff = timezone.now() - timedelta(seconds=OTPRequest.RESEND_COOLDOWN_SECONDS)
        if identity.otp_requests.filter(created_at__gte=cooldown_cutoff).exists():
            return Response(
                {"detail": "Please wait before requesting another OTP."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Generate and store OTP
        otp = OTPRequest.generate_otp()
        OTPRequest.objects.create(
            identity=identity,
            otp_hash=OTPRequest.hash_otp(otp),
            expires_at=timezone.now() + timedelta(minutes=OTPRequest.OTP_EXPIRY_MINUTES),
        )

        # TODO: replace with email provider (SendGrid, etc.)
        logger.info("OTP for %s: %s", email, otp)

        return Response({"detail": "OTP sent."}, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OTPVerifySerializer,
        responses={200: {"type": "object", "properties": {
            "access": {"type": "string"},
            "refresh": {"type": "string"},
        }}},
        summary="Verify OTP",
        description="Verify the OTP and receive JWT access and refresh tokens.",
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].lower()
        otp = serializer.validated_data["otp"]

        try:
            identity = Identity.objects.get(provider=Identity.PROVIDER_EMAIL, identifier=email)
        except Identity.DoesNotExist:
            return Response(
                {"detail": "Invalid email or OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Find the latest usable OTP request
        otp_request = (
            identity.otp_requests
            .filter(verified_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

        if not otp_request or not otp_request.is_usable:
            return Response(
                {"detail": "OTP has expired or is no longer valid. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not otp_request.check_otp(otp):
            otp_request.attempts += 1
            otp_request.save(update_fields=["attempts"])
            return Response(
                {"detail": "Invalid OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark OTP and Identity as verified
        now = timezone.now()
        otp_request.verified_at = now
        otp_request.save(update_fields=["verified_at"])

        if not identity.verified_at:
            identity.verified_at = now
            identity.save(update_fields=["verified_at"])

        return Response(_issue_tokens(identity.user), status=status.HTTP_200_OK)
