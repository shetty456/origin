import pytest
from datetime import timedelta
from django.utils import timezone

from core.identity.models import Identity, OTPRequest


@pytest.mark.django_db
class TestOTPGeneration:
    def test_generate_otp_is_four_digits(self):
        otp = OTPRequest.generate_otp()
        assert len(otp) == 4
        assert otp.isdigit()

    def test_generate_otp_zero_padded(self):
        # The OTP is always exactly 4 chars even for small numbers.
        # Run enough times to have high confidence zero-padding works.
        otps = {OTPRequest.generate_otp() for _ in range(200)}
        assert all(len(o) == 4 for o in otps)

    def test_hash_otp_is_deterministic(self):
        assert OTPRequest.hash_otp("1234") == OTPRequest.hash_otp("1234")

    def test_hash_otp_different_values(self):
        assert OTPRequest.hash_otp("1234") != OTPRequest.hash_otp("5678")

    def test_hash_otp_is_64_chars(self):
        assert len(OTPRequest.hash_otp("1234")) == 64

    def test_check_otp_correct(self):
        otp = "1234"
        req = OTPRequest(otp_hash=OTPRequest.hash_otp(otp), expires_at=timezone.now() + timedelta(minutes=10))
        assert req.check_otp(otp) is True

    def test_check_otp_wrong(self):
        req = OTPRequest(otp_hash=OTPRequest.hash_otp("1234"), expires_at=timezone.now() + timedelta(minutes=10))
        assert req.check_otp("9999") is False


@pytest.mark.django_db
class TestOTPProperties:
    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user()
        self.identity = Identity.objects.create(
            user=self.user, provider=Identity.PROVIDER_EMAIL, identifier="props@example.com"
        )

    def _make_otp(self, expires_delta=timedelta(minutes=10), attempts=0, verified=False):
        req = OTPRequest.objects.create(
            identity=self.identity,
            otp_hash=OTPRequest.hash_otp("1234"),
            expires_at=timezone.now() + expires_delta,
            attempts=attempts,
        )
        if verified:
            OTPRequest.objects.filter(pk=req.pk).update(verified_at=timezone.now())
            req.refresh_from_db()
        return req

    def test_is_expired_false(self):
        req = self._make_otp()
        assert req.is_expired is False

    def test_is_expired_true(self):
        req = self._make_otp(expires_delta=timedelta(minutes=-1))
        assert req.is_expired is True

    def test_is_verified_false(self):
        req = self._make_otp()
        assert req.is_verified is False

    def test_is_verified_true(self):
        req = self._make_otp(verified=True)
        assert req.is_verified is True

    def test_is_exhausted_at_max(self):
        req = self._make_otp(attempts=OTPRequest.MAX_ATTEMPTS)
        assert req.is_exhausted is True

    def test_is_exhausted_below_max(self):
        req = self._make_otp(attempts=OTPRequest.MAX_ATTEMPTS - 1)
        assert req.is_exhausted is False

    def test_is_usable_valid(self):
        req = self._make_otp()
        assert req.is_usable is True

    def test_is_usable_expired(self):
        req = self._make_otp(expires_delta=timedelta(minutes=-1))
        assert req.is_usable is False

    def test_is_usable_verified(self):
        req = self._make_otp(verified=True)
        assert req.is_usable is False

    def test_is_usable_exhausted(self):
        req = self._make_otp(attempts=OTPRequest.MAX_ATTEMPTS)
        assert req.is_usable is False


@pytest.mark.django_db
class TestOTPRequestManager:
    def setup_method(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user()
        self.identity = Identity.objects.create(
            user=self.user, provider=Identity.PROVIDER_EMAIL, identifier="mgr@example.com"
        )

    def test_create_for_stores_hash_not_plaintext(self):
        req, otp = OTPRequest.objects.create_for(self.identity)
        assert req.otp_hash != otp
        assert len(req.otp_hash) == 64

    def test_create_for_expires_in_future(self):
        req, _ = OTPRequest.objects.create_for(self.identity)
        assert req.expires_at > timezone.now()

    def test_create_for_sets_correct_expiry(self):
        before = timezone.now()
        req, _ = OTPRequest.objects.create_for(self.identity)
        expected = before + timedelta(minutes=OTPRequest.OTP_EXPIRY_MINUTES)
        assert abs((req.expires_at - expected).total_seconds()) < 2

    def test_get_latest_usable_returns_newest(self):
        req1, _ = OTPRequest.objects.create_for(self.identity)
        req2, _ = OTPRequest.objects.create_for(self.identity)
        result = OTPRequest.objects.get_latest_usable(self.identity)
        assert result.pk == req2.pk

    def test_get_latest_usable_ignores_verified(self):
        req, otp = OTPRequest.objects.create_for(self.identity)
        OTPRequest.objects.filter(pk=req.pk).update(verified_at=timezone.now())
        result = OTPRequest.objects.get_latest_usable(self.identity)
        assert result is None

    def test_get_latest_usable_none_when_empty(self):
        assert OTPRequest.objects.get_latest_usable(self.identity) is None

    def test_is_on_cooldown_true(self):
        OTPRequest.objects.create_for(self.identity)
        assert OTPRequest.objects.is_on_cooldown(self.identity) is True

    def test_is_on_cooldown_false_after_window(self):
        OTPRequest.objects.create_for(self.identity)
        # Manually backdate the created_at beyond the cooldown window.
        cooldown = timedelta(seconds=OTPRequest.RESEND_COOLDOWN_SECONDS + 1)
        OTPRequest.objects.filter(identity=self.identity).update(
            created_at=timezone.now() - cooldown
        )
        assert OTPRequest.objects.is_on_cooldown(self.identity) is False

    def test_is_on_cooldown_false_when_empty(self):
        assert OTPRequest.objects.is_on_cooldown(self.identity) is False


@pytest.mark.django_db
class TestIdentityManager:
    def test_get_or_create_for_email_creates_user_and_identity(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        identity, created = Identity.objects.get_or_create_for_email("new@example.com")
        assert created is True
        assert identity.provider == Identity.PROVIDER_EMAIL
        assert identity.identifier == "new@example.com"
        assert User.objects.filter(pk=identity.user_id).exists()

    def test_get_or_create_for_email_returns_existing(self):
        Identity.objects.get_or_create_for_email("existing@example.com")
        identity, created = Identity.objects.get_or_create_for_email("existing@example.com")
        assert created is False

    def test_get_or_create_for_phone_creates_user_and_identity(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        identity, created = Identity.objects.get_or_create_for_phone("+15005550006")
        assert created is True
        assert identity.provider == Identity.PROVIDER_PHONE
        assert User.objects.filter(pk=identity.user_id).exists()

    def test_get_or_create_for_link_creates_identity(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user()
        identity, created = Identity.objects.get_or_create_for_link(
            user, Identity.PROVIDER_EMAIL, "link@example.com"
        )
        assert created is True
        assert identity.user_id == user.pk

    def test_get_or_create_for_link_raises_if_claimed_by_other_user(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user1 = User.objects.create_user()
        user2 = User.objects.create_user()
        Identity.objects.create(
            user=user1, provider=Identity.PROVIDER_EMAIL, identifier="claimed@example.com",
            verified_at=timezone.now(),
        )
        with pytest.raises(ValueError):
            Identity.objects.get_or_create_for_link(user2, Identity.PROVIDER_EMAIL, "claimed@example.com")

    def test_get_or_create_for_email_reuses_abandoned_signup(self):
        """An unverified identity with no other verified identities should be reused."""
        identity_first, _ = Identity.objects.get_or_create_for_email("abandoned@example.com")
        assert identity_first.is_verified is False
        identity_second, created = Identity.objects.get_or_create_for_email("abandoned@example.com")
        assert created is False
        assert identity_second.pk == identity_first.pk

    def test_get_or_create_for_email_reassigns_abandoned_link_attempt(self):
        """Unverified identity whose user has other verified identities gets a new user."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user()
        # Give the user a verified phone identity so they have a real account.
        Identity.objects.create(
            user=user, provider=Identity.PROVIDER_PHONE, identifier="+15005550001",
            verified_at=timezone.now(),
        )
        # Create unverified email identity on the same user (simulates abandoned link).
        Identity.objects.create(
            user=user, provider=Identity.PROVIDER_EMAIL, identifier="link-attempt@example.com",
        )
        identity, created = Identity.objects.get_or_create_for_email("link-attempt@example.com")
        assert created is False
        # Identity must now belong to a fresh user, not the original account holder.
        assert identity.user_id != user.pk
