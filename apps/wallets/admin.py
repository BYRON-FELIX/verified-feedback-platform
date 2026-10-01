from django.contrib import admin

from .models import Wallet, WalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "available_balance", "pending_balance",
                    "lifetime_earnings", "lifetime_withdrawn", "currency")
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "wallet", "transaction_type",
                    "amount", "balance_after", "description")
    list_filter = ("transaction_type",)
    search_fields = ("wallet__user__email", "description", "reference_id")
    readonly_fields = tuple(f.name for f in WalletTransaction._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser