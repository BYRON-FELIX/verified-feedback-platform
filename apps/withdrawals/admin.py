from django.contrib import admin

from .models import Withdrawal


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = (
        "requested_at", "user", "amount_ksh", "net_amount_ksh",
        "tax_withheld_ksh", "destination_phone", "status", "provider",
        "provider_reference",
    )
    list_filter = ("status", "provider")
    search_fields = ("user__email", "destination_phone", "provider_reference")

    # Lock down fields that must be changed only via the service layer
    readonly_fields = (
        "id", "wallet", "user", "amount_ksh", "fee_ksh", "tax_withheld_ksh",
        "net_amount_ksh", "requested_at", "processed_at", "completed_at",
        "provider_response", "idempotency_key", "status", "processed_by",
        "provider_reference", "failure_reason",
    )

    fieldsets = (
        ("Withdrawal", {
            "fields": ("id", "user", "wallet", "status",
                       "amount_ksh", "fee_ksh", "tax_withheld_ksh", "net_amount_ksh")
        }),
        ("Destination", {
            "fields": ("provider", "destination_phone", "provider_reference")
        }),
        ("Timeline", {
            "fields": ("requested_at", "processed_at", "completed_at", "processed_by")
        }),
        ("Meta", {
            "fields": ("idempotency_key", "provider_response", "failure_reason")
        }),
    )

    def has_add_permission(self, request):
        # Withdrawals are created only via request_withdrawal()
        return False

    def has_delete_permission(self, request, obj=None):
        # Never delete a withdrawal; it's part of the financial ledger
        return False