import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserManager:
    def test_create_user_with_email(self):
        user = User.objects.create_user(email="alice@example.com", name="Alice")
        assert user.email == "alice@example.com"
        assert user.name == "Alice"
        assert user.is_active is True
        assert user.is_staff is False

    def test_create_user_without_email(self):
        user = User.objects.create_user()
        assert user.email is None
        assert user.is_active is True

    def test_create_user_id_is_uuid(self):
        import uuid
        user = User.objects.create_user(email="bob@example.com")
        assert isinstance(user.id, uuid.UUID)

    def test_create_superuser(self):
        user = User.objects.create_superuser(email="admin@example.com", password="secret")
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_user_str_with_email(self):
        user = User.objects.create_user(email="carol@example.com")
        assert str(user) == "carol@example.com"

    def test_user_str_without_email(self):
        user = User.objects.create_user()
        assert str(user) == str(user.id)

    def test_email_unique(self):
        from django.db import IntegrityError
        User.objects.create_user(email="dup@example.com")
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="dup@example.com")

    def test_multiple_users_without_email(self):
        u1 = User.objects.create_user()
        u2 = User.objects.create_user()
        assert u1.pk != u2.pk
