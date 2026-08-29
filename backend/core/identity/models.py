from django.conf import settings
from django.db import models


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
        # One identifier per provider globally — prevents duplicate accounts
        unique_together = [("provider", "identifier")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider}:{self.identifier}"

    @property
    def is_verified(self):
        return self.verified_at is not None
