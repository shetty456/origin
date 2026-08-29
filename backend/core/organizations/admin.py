from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import Organization, Membership


class MembershipInline(TabularInline):
    model = Membership
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("user", "role", "created_at")


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ("name", "slug", "display_active", "created_at")
    list_display_links = ("name", "slug")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]

    fieldsets = (
        ("Organization", {
            "classes": ["tab"],
            "fields": ("id", "name", "slug", "is_active"),
        }),
        ("Timestamps", {
            "classes": ["tab"],
            "fields": ("created_at", "updated_at"),
        }),
    )

    @display(description="Active", boolean=True, ordering="is_active")
    def display_active(self, obj):
        return obj.is_active


@admin.register(Membership)
class MembershipAdmin(ModelAdmin):
    list_display = ("user", "organization", "display_role", "created_at")
    list_display_links = ("user", "organization")
    list_filter = ("role",)
    search_fields = ("user__email", "user__name", "organization__name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Membership", {
            "classes": ["tab"],
            "fields": ("user", "organization", "role"),
        }),
        ("Timestamps", {
            "classes": ["tab"],
            "fields": ("created_at", "updated_at"),
        }),
    )

    @display(description="Role", label=True, ordering="role")
    def display_role(self, obj):
        return obj.role
