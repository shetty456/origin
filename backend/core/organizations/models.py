import uuid
from django.conf import settings
from django.db import models


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLE_OWNER = "owner"
    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"

    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_MEMBER, "Member"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "memberships"
        unique_together = [("user", "organization")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.organization} ({self.role})"

    @property
    def is_owner(self):
        return self.role == self.ROLE_OWNER

    @property
    def is_admin(self):
        return self.role in (self.ROLE_OWNER, self.ROLE_ADMIN)
