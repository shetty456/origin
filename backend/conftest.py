import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.identity.models import Identity, OTPRequest
from core.organizations.models import Organization, Membership

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(email=None, name="Test User", **kwargs):
        return User.objects.create_user(email=email, name=name, **kwargs)
    return _make


@pytest.fixture
def make_identity(db):
    def _make(user, provider=Identity.PROVIDER_EMAIL, identifier="test@example.com", verified=True):
        return Identity.objects.create(
            user=user,
            provider=provider,
            identifier=identifier,
            verified_at=timezone.now() if verified else None,
        )
    return _make


@pytest.fixture
def make_otp(db):
    """Create an OTPRequest for an identity and return (otp_request, plaintext_otp)."""
    def _make(identity):
        return OTPRequest.objects.create_for(identity)
    return _make


@pytest.fixture
def make_org(db):
    def _make(name="Test Org", slug="test-org"):
        return Organization.objects.create(name=name, slug=slug)
    return _make


@pytest.fixture
def make_membership(db):
    def _make(user, org, role=Membership.ROLE_MEMBER):
        return Membership.objects.create(user=user, organization=org, role=role)
    return _make


@pytest.fixture
def auth_client(api_client, make_user, make_identity):
    user = make_user(email="auth@example.com")
    make_identity(user, identifier="auth@example.com")
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    api_client.user = user
    return api_client
