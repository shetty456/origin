from django.contrib import admin

from .models import Organization, Membership


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("user", "role", "created_at")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("user__email", "user__name", "organization__name")
    readonly_fields = ("created_at", "updated_at")
