"""Django Admin configuration for custom User and Profile models."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Student / Instructor Profile"
    fk_name = "user"
    fields = ("display_name", "country", "timezone", "audience_override")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-created_at",)
    list_display = (
        "email",
        "email_verified",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("email_verified", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "profile__display_name", "profile__country")
    readonly_fields = ("id", "created_at", "updated_at", "last_login", "date_joined")
    inlines = (ProfileInline,)

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "email_verified")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "email_verified",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
