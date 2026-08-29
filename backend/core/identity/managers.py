from datetime import timedelta
from django.db import models, transaction, IntegrityError
from django.db.models import F
from django.utils import timezone


class IdentityManager(models.Manager):
    def get_by_provider(self, provider, identifier):
        return self.get(provider=provider, identifier=identifier)

    def get_or_create_for_email(self, email):
        """
        Find or create an Identity + User for the given email. Returns (identity, created).

        Cases handled:
        1. Verified Identity exists → return it (existing user, normal login).
        2. Unverified Identity exists, owned by a user with no other verified
           identities (abandoned signup) → reuse it, a new OTP will re-verify.
        3. Unverified Identity exists, owned by a user with other verified
           identities (abandoned link attempt) → reassign to a new User so a
           new signup is never hijacked into another user's account.
        4. No Identity, User exists with this email (e.g. createsuperuser) →
           create Identity for them.
        5. Nothing exists → create both User and Identity.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            identity = self.get(provider="email", identifier=email)

            if not identity.is_verified:
                # Check if this identity's user has other verified identities.
                # If so, this was an abandoned link attempt — reassign to a new user.
                has_other_verified = identity.user.identities.filter(
                    verified_at__isnull=False
                ).exists()
                if has_other_verified:
                    with transaction.atomic():
                        user = User.objects.create_user(email=email)
                        identity.user = user
                        identity.save(update_fields=["user", "updated_at"])

            return identity, False
        except self.model.DoesNotExist:
            try:
                with transaction.atomic():
                    try:
                        user = User.objects.get(email=email)
                    except User.DoesNotExist:
                        user = User.objects.create_user(email=email)
                    identity = self.create(
                        user=user,
                        provider="email",
                        identifier=email,
                    )
                return identity, True
            except IntegrityError:
                # Another request created the identity in a race — re-fetch it.
                identity = self.get(provider="email", identifier=email)
                return identity, False

    def get_or_create_for_phone(self, phone):
        """
        Find or create an Identity + User for the given phone (E.164). Returns (identity, created).
        Applies the same abandoned-link-attempt guard as get_or_create_for_email.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            identity = self.get(provider="phone", identifier=phone)

            if not identity.is_verified:
                has_other_verified = identity.user.identities.filter(
                    verified_at__isnull=False
                ).exists()
                if has_other_verified:
                    with transaction.atomic():
                        user = User.objects.create_user()
                        identity.user = user
                        identity.save(update_fields=["user", "updated_at"])

            return identity, False
        except self.model.DoesNotExist:
            try:
                with transaction.atomic():
                    user = User.objects.create_user()
                    identity = self.create(
                        user=user,
                        provider="phone",
                        identifier=phone,
                    )
                return identity, True
            except IntegrityError:
                identity = self.get(provider="phone", identifier=phone)
                return identity, False


    def get_or_create_for_link(self, user, provider, identifier):
        """
        Prepare an Identity for linking to an existing authenticated user.
        Returns (identity, created).
        Raises ValueError if the identifier is already claimed by a different user.
        """
        try:
            identity = self.get(provider=provider, identifier=identifier)
            if identity.user_id != user.pk:
                raise ValueError(
                    f"This {provider} identifier is already linked to another account."
                )
            return identity, False  # Already linked to this user
        except self.model.DoesNotExist:
            try:
                with transaction.atomic():
                    identity = self.create(
                        user=user,
                        provider=provider,
                        identifier=identifier,
                        # verified_at intentionally left null until OTP is confirmed
                    )
                return identity, True
            except IntegrityError:
                # Concurrent request created the same identity — re-fetch and check ownership.
                identity = self.get(provider=provider, identifier=identifier)
                if identity.user_id != user.pk:
                    raise ValueError(
                        f"This {provider} identifier is already linked to another account."
                    )
                return identity, False


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
