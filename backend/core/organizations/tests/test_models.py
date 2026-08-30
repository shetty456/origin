import pytest
from django.db import IntegrityError

from core.organizations.models import Organization, Membership


@pytest.mark.django_db
class TestOrganization:
    def test_create(self):
        org = Organization.objects.create(name="Acme", slug="acme")
        assert org.name == "Acme"
        assert org.slug == "acme"
        assert org.is_active is True

    def test_slug_unique(self):
        Organization.objects.create(name="Acme", slug="acme")
        with pytest.raises(IntegrityError):
            Organization.objects.create(name="Acme 2", slug="acme")

    def test_str(self):
        org = Organization.objects.create(name="Acme", slug="acme")
        assert str(org) == "Acme"


@pytest.mark.django_db
class TestMembership:
    def test_create_member(self, make_user, make_org):
        user = make_user()
        org = make_org()
        membership = Membership.objects.create(user=user, organization=org, role=Membership.ROLE_MEMBER)
        assert membership.role == Membership.ROLE_MEMBER

    def test_is_owner(self, make_user, make_org):
        user = make_user()
        org = make_org()
        m = Membership.objects.create(user=user, organization=org, role=Membership.ROLE_OWNER)
        assert m.is_owner is True
        assert m.is_admin is True

    def test_is_admin(self, make_user, make_org):
        user = make_user()
        org = make_org()
        m = Membership.objects.create(user=user, organization=org, role=Membership.ROLE_ADMIN)
        assert m.is_owner is False
        assert m.is_admin is True

    def test_member_is_not_admin(self, make_user, make_org):
        user = make_user()
        org = make_org()
        m = Membership.objects.create(user=user, organization=org, role=Membership.ROLE_MEMBER)
        assert m.is_owner is False
        assert m.is_admin is False

    def test_unique_membership(self, make_user, make_org):
        user = make_user()
        org = make_org()
        Membership.objects.create(user=user, organization=org, role=Membership.ROLE_MEMBER)
        with pytest.raises(IntegrityError):
            Membership.objects.create(user=user, organization=org, role=Membership.ROLE_ADMIN)
