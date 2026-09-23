from django.contrib import admin

from .models import Withdrawal


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = (
        "requested_at", "user", "amount", "net_amount",
        "tax_withheld", "fee", "provider", "status",
        "provider_reference",
    )
    list_filter = ("status", "provider")
    search_fields = ("user__email", "destination_phone", "destination_email", "provider_reference")
    readonly_fields = (
        "id", "wallet", "user", "amount", "fee", "tax_withheld",
        "net_amount", "requested_at", "processed_at", "completed_at",
        "provider_response", "idempotency_key", "status", "processed_by",
        "provider_reference", "failure_reason",
    )

    fieldsets = (
        ("Withdrawal", {
            "fields": ("id", "user", "wallet", "status",
                       "amount", "fee", "tax_withheld", "net_amount")
        }),
        ("Destination", {
            "fields": ("provider", "destination_phone", "destination_email",
                       "provider_reference")
        }),
        ("Timeline", {
            "fields": ("requested_at", "processed_at", "completed_at", "processed_by")
        }),
        ("Meta", {
            "fields": ("idempotency_key", "provider_response", "failure_reason")
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False