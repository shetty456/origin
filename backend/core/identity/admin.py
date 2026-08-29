from django.contrib import admin

from .models import Identity


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "identifier", "is_verified", "created_at")
    list_filter = ("provider",)
    search_fields = ("identifier", "user__email", "user__name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
