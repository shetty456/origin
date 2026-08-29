import hashlib
import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone


class Identity(models.Model):
    PROVIDER_EMAIL = "email"
    PROVIDER_PHONE = "phone"
    PROVIDER_GOOGLE = "google"
    PROVIDER_APPLE = "apple"

    PROVIDER_CHOICES = [
        (PROVIDER_EMAIL, "Email"),
        (PROVIDER_PHONE, "Phone"),
        (PROVIDER_GOOGLE, "Google"),
        (PROVIDER_APPLE, "Apple"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="identities",
    )
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    # The unique identifier for this provider: email address, phone number, OAuth subject ID, etc.
    identifier = models.CharField(max_length=255)
    verified_at = models.DateTimeField(null=True, blank=True)
    # Stores provider-specific data: OAuth tokens, profile info, etc.
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identities"
        unique_together = [("provider", "identifier")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider}:{self.identifier}"

    @property
    def is_verified(self):
        return self.verified_at is not None


class OTPRequest(models.Model):
    MAX_ATTEMPTS = 5
    OTP_EXPIRY_MINUTES = 10
    RESEND_COOLDOWN_SECONDS = 60

    identity = models.ForeignKey(
        Identity,
        on_delete=models.CASCADE,
        related_name="otp_requests",
    )
    # SHA-256 hash of the OTP — never stored in plaintext
    otp_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "otp_requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP for {self.identity} at {self.created_at}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_verified(self):
        return self.verified_at is not None

    @property
    def is_exhausted(self):
        return self.attempts >= self.MAX_ATTEMPTS

    @property
    def is_usable(self):
        return not self.is_expired and not self.is_verified and not self.is_exhausted

    @staticmethod
    def hash_otp(otp: str) -> str:
        return hashlib.sha256(otp.encode()).hexdigest()

    @staticmethod
    def generate_otp() -> str:
        return str(secrets.randbelow(1000000)).zfill(6)

    def check_otp(self, otp: str) -> bool:
        return self.otp_hash == self.hash_otp(otp)
