from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "purpose",
        "amount_usd",
        "amount_kes",
        "status",
        "provider_reference",
    )
    list_filter = ("purpose", "status")
    search_fields = ("user__email", "external_reference", "provider_reference")
    readonly_fields = tuple(field.name for field in Payment._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
