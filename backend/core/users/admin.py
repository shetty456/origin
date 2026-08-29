from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.decorators import display

from .models import User


@admin.register(User)
class UserAdmin(ModelAdmin, BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ("email", "name", "display_active", "display_staff", "created_at")
    list_display_links = ("email", "name")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "name")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        ("Account", {
            "classes": ["tab"],
            "fields": ("id", "email", "password"),
        }),
        ("Personal", {
            "classes": ["tab"],
            "fields": ("name",),
        }),
        ("Permissions", {
            "classes": ["tab"],
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        ("Timestamps", {
            "classes": ["tab"],
            "fields": ("created_at", "updated_at"),
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2"),
        }),
    )

    @display(description="Active", boolean=True, ordering="is_active")
    def display_active(self, obj):
        return obj.is_active

    @display(description="Staff", boolean=True, ordering="is_staff")
    def display_staff(self, obj):
        return obj.is_staff
