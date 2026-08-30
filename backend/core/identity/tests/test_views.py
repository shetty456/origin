import pytest
from django.urls import reverse
from django.utils import timezone

from core.identity.models import Identity, OTPRequest


EMAIL = "test@example.com"
PHONE = "+15005550006"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def request_email_otp(client, email=EMAIL):
    return client.post(reverse("otp-email-request"), {"email": email})


def verify_email_otp(client, otp, email=EMAIL):
    return client.post(reverse("otp-email-verify"), {"email": email, "otp": otp})


def request_phone_otp(client, phone=PHONE):
    return client.post(reverse("otp-phone-request"), {"phone": phone})


def verify_phone_otp(client, otp, phone=PHONE):
    return client.post(reverse("otp-phone-verify"), {"phone": phone, "otp": otp})


def _get_otp_for_email(email):
    identity = Identity.objects.get(provider=Identity.PROVIDER_EMAIL, identifier=email)
    req = OTPRequest.objects.get_latest_usable(identity)
    from core.identity.models import OTPRequest as OTP
    # Retrieve the stored hash and brute-force the 4-digit space to find the plaintext.
    for i in range(10000):
        candidate = str(i).zfill(4)
        if req.check_otp(candidate):
            return candidate
    raise AssertionError("Could not recover OTP from hash")


def _get_otp_for_identity(identity):
    req = OTPRequest.objects.get_latest_usable(identity)
    for i in range(10000):
        candidate = str(i).zfill(4)
        if req.check_otp(candidate):
            return candidate
    raise AssertionError("Could not recover OTP from hash")


# ---------------------------------------------------------------------------
# Email OTP — signup / login
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestEmailOTPRequest:
    def test_returns_200(self, api_client):
        res = request_email_otp(api_client)
        assert res.status_code == 200

    def test_creates_identity(self, api_client):
        request_email_otp(api_client)
        assert Identity.objects.filter(provider=Identity.PROVIDER_EMAIL, identifier=EMAIL).exists()

    def test_returns_429_on_cooldown(self, api_client):
        request_email_otp(api_client)
        res = request_email_otp(api_client)
        assert res.status_code == 429

    def test_invalid_email_returns_400(self, api_client):
        res = api_client.post(reverse("otp-email-request"), {"email": "not-an-email"})
        assert res.status_code == 400


@pytest.mark.django_db
class TestEmailOTPVerify:
    def test_correct_otp_returns_tokens(self, api_client):
        request_email_otp(api_client)
        otp = _get_otp_for_email(EMAIL)
        res = verify_email_otp(api_client, otp)
        assert res.status_code == 200
        assert "access" in res.data
        assert "refresh" in res.data

    def test_correct_otp_marks_identity_verified(self, api_client):
        request_email_otp(api_client)
        otp = _get_otp_for_email(EMAIL)
        verify_email_otp(api_client, otp)
        identity = Identity.objects.get(provider=Identity.PROVIDER_EMAIL, identifier=EMAIL)
        assert identity.is_verified is True

    def test_wrong_otp_returns_400(self, api_client):
        request_email_otp(api_client)
        res = verify_email_otp(api_client, "0000")
        assert res.status_code == 400

    def test_wrong_otp_increments_attempts(self, api_client):
        request_email_otp(api_client)
        verify_email_otp(api_client, "0000")
        identity = Identity.objects.get(provider=Identity.PROVIDER_EMAIL, identifier=EMAIL)
        req = OTPRequest.objects.filter(identity=identity).first()
        assert req.attempts == 1

    def test_max_attempts_exhausts_otp(self, api_client):
        request_email_otp(api_client)
        for _ in range(OTPRequest.MAX_ATTEMPTS):
            verify_email_otp(api_client, "0000")
        identity = Identity.objects.get(provider=Identity.PROVIDER_EMAIL, identifier=EMAIL)
        req = OTPRequest.objects.filter(identity=identity).first()
        assert req.is_exhausted is True

    def test_exhausted_otp_returns_400(self, api_client):
        request_email_otp(api_client)
        identity = Identity.objects.get(provider=Identity.PROVIDER_EMAIL, identifier=EMAIL)
        otp_req = OTPRequest.objects.filter(identity=identity).first()
        OTPRequest.objects.filter(pk=otp_req.pk).update(attempts=OTPRequest.MAX_ATTEMPTS)
        otp = _get_otp_for_email(EMAIL)
        res = verify_email_otp(api_client, otp)
        assert res.status_code == 400

    def test_expired_otp_returns_400(self, api_client):
        request_email_otp(api_client)
        identity = Identity.objects.get(provider=Identity.PROVIDER_EMAIL, identifier=EMAIL)
        # Backdate expiry to the past.
        from datetime import timedelta
        OTPRequest.objects.filter(identity=identity).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        otp = _get_otp_for_email(EMAIL)
        res = verify_email_otp(api_client, otp)
        assert res.status_code == 400

    def test_replay_returns_400(self, api_client):
        """A correct OTP cannot be used twice."""
        request_email_otp(api_client)
        otp = _get_otp_for_email(EMAIL)
        verify_email_otp(api_client, otp)
        res = verify_email_otp(api_client, otp)
        assert res.status_code == 400

    def test_unknown_email_returns_400(self, api_client):
        res = verify_email_otp(api_client, "1234", email="unknown@example.com")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Phone OTP — signup / login
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPhoneOTPRequest:
    def test_returns_200(self, api_client):
        res = request_phone_otp(api_client)
        assert res.status_code == 200

    def test_creates_identity(self, api_client):
        request_phone_otp(api_client)
        assert Identity.objects.filter(provider=Identity.PROVIDER_PHONE, identifier=PHONE).exists()

    def test_returns_429_on_cooldown(self, api_client):
        request_phone_otp(api_client)
        res = request_phone_otp(api_client)
        assert res.status_code == 429

    def test_invalid_phone_returns_400(self, api_client):
        res = api_client.post(reverse("otp-phone-request"), {"phone": "notaphone"})
        assert res.status_code == 400


@pytest.mark.django_db
class TestPhoneOTPVerify:
    def test_correct_otp_returns_tokens(self, api_client):
        request_phone_otp(api_client)
        identity = Identity.objects.get(provider=Identity.PROVIDER_PHONE, identifier=PHONE)
        otp = _get_otp_for_identity(identity)
        res = verify_phone_otp(api_client, otp)
        assert res.status_code == 200
        assert "access" in res.data
        assert "refresh" in res.data

    def test_wrong_otp_returns_400(self, api_client):
        request_phone_otp(api_client)
        res = verify_phone_otp(api_client, "0000")
        assert res.status_code == 400

    def test_unknown_phone_returns_400(self, api_client):
        res = verify_phone_otp(api_client, "1234", phone="+15005550007")
        assert res.status_code == 400


# ---------------------------------------------------------------------------
# Identity linking
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestIdentityLinking:
    def test_link_email_request_returns_200(self, auth_client):
        res = auth_client.post(
            reverse("link-email-request"), {"email": "linked@example.com"}
        )
        assert res.status_code == 200

    def test_link_email_request_requires_auth(self, api_client):
        res = api_client.post(
            reverse("link-email-request"), {"email": "linked@example.com"}
        )
        assert res.status_code == 401

    def test_link_email_verify_links_identity(self, auth_client):
        email = "tolink@example.com"
        auth_client.post(reverse("link-email-request"), {"email": email})
        identity = Identity.objects.get(provider=Identity.PROVIDER_EMAIL, identifier=email)
        otp = _get_otp_for_identity(identity)
        res = auth_client.post(reverse("link-email-verify"), {"email": email, "otp": otp})
        assert res.status_code == 200
        identity.refresh_from_db()
        assert identity.is_verified is True
        assert identity.user_id == auth_client.user.pk

    def test_link_email_request_conflict_with_other_user(self, auth_client, make_user, make_identity):
        other_user = make_user(email="other@example.com")
        make_identity(other_user, identifier="taken@example.com")
        res = auth_client.post(reverse("link-email-request"), {"email": "taken@example.com"})
        assert res.status_code == 409

    def test_link_phone_request_returns_200(self, auth_client):
        res = auth_client.post(reverse("link-phone-request"), {"phone": PHONE})
        assert res.status_code == 200

    def test_link_phone_verify_links_identity(self, auth_client):
        auth_client.post(reverse("link-phone-request"), {"phone": PHONE})
        identity = Identity.objects.get(provider=Identity.PROVIDER_PHONE, identifier=PHONE)
        otp = _get_otp_for_identity(identity)
        res = auth_client.post(reverse("link-phone-verify"), {"phone": PHONE, "otp": otp})
        assert res.status_code == 200
        identity.refresh_from_db()
        assert identity.is_verified is True
