from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-created_at",)
    list_display = (
        "email", "username", "role",
        "is_email_verified", "is_phone_verified",
        "is_active", "is_suspended", "created_at",
    )
    list_filter = ("role", "is_active", "is_staff", "is_suspended",
                   "is_email_verified", "is_phone_verified")
    search_fields = ("email", "username", "phone_number")

    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Contact", {"fields": ("phone_number",)}),
        ("Verification", {"fields": ("is_email_verified", "is_phone_verified")}),
        ("Permissions", {"fields": ("role", "is_active", "is_staff", "is_superuser",
                                     "groups", "user_permissions")}),
        ("Suspension", {"fields": ("is_suspended", "suspension_reason", "suspended_at")}),
        ("Important dates", {"fields": ("last_login", "last_login_ip",
                                         "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "last_login", "suspended_at", "last_login_ip")

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2", "role"),
        }),
    )