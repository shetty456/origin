from datetime import timedelta
from django.db import models
from django.utils import timezone


class IdentityManager(models.Manager):
    def get_by_provider(self, provider, identifier):
        return self.get(provider=provider, identifier=identifier)

    def get_or_create_for_email(self, email):
        """
        Find or create an Identity + User for the given email.
        Returns (identity, created).
        Lazy-imports User to avoid circular dependency.
        """
        from core.users.models import User

        try:
            identity = self.get(provider="email", identifier=email)
            return identity, False
        except self.model.DoesNotExist:
            user = User.objects.create_user(email=email)
            identity = self.create(
                user=user,
                provider="email",
                identifier=email,
            )
            return identity, True


class OTPRequestManager(models.Manager):
    def get_latest_usable(self, identity):
        """Return the latest unverified OTP request for this identity, or None."""
        return (
            self.filter(identity=identity, verified_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

    def is_on_cooldown(self, identity):
        """True if an OTP was requested within the resend cooldown window."""
        cutoff = timezone.now() - timedelta(seconds=self.model.RESEND_COOLDOWN_SECONDS)
        return self.filter(identity=identity, created_at__gte=cutoff).exists()

    def create_for(self, identity):
        """
        Generate a new OTP for the given identity.
        Returns (otp_request, plaintext_otp).
        The plaintext OTP must be sent to the user — it is never stored.
        """
        otp = self.model.generate_otp()
        otp_request = self.create(
            identity=identity,
            otp_hash=self.model.hash_otp(otp),
            expires_at=timezone.now() + timedelta(minutes=self.model.OTP_EXPIRY_MINUTES),
        )
        return otp_request, otp
