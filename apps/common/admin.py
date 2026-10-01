from django.contrib import admin

from .models import PlatformSettings


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "verification_trigger_usd",
        "premium_unlock_trigger_usd",
        "premium_unlock_cost_usd",
        "mpesa_account_verification_fee_usd",
        "updated_at",
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not PlatformSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
