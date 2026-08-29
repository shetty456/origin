from django.contrib import admin

from .models import Identity, OTPRequest


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "identifier", "is_verified", "created_at")
    list_filter = ("provider",)
    search_fields = ("identifier", "user__email", "user__name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_display = ("identity", "is_verified", "is_expired", "attempts", "created_at", "expires_at")
    list_filter = ("identity__provider",)
    search_fields = ("identity__identifier",)
    readonly_fields = ("otp_hash", "created_at", "expires_at", "verified_at", "attempts")
    ordering = ("-created_at",)
