from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Identity


@admin.register(Identity)
class IdentityAdmin(ModelAdmin):
    list_display = ("user", "display_provider", "identifier", "display_verified", "created_at")
    list_display_links = ("user", "identifier")
    list_filter = ("provider",)
    search_fields = ("identifier", "user__email", "user__name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    fieldsets = (
        ("Identity", {
            "classes": ["tab"],
            "fields": ("user", "provider", "identifier"),
        }),
        ("Verification", {
            "classes": ["tab"],
            "fields": ("verified_at", "metadata"),
        }),
        ("Timestamps", {
            "classes": ["tab"],
            "fields": ("created_at", "updated_at"),
        }),
    )

    @display(description="Provider", label=True, ordering="provider")
    def display_provider(self, obj):
        return obj.provider

    @display(description="Verified", boolean=True, ordering="verified_at")
    def display_verified(self, obj):
        return obj.is_verified
