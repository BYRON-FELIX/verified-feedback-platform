from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import admin
from django.db.models import Count, Sum
from django.utils import timezone

from .models import Payment, PaymentStatus


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
        "mpesa_transaction_code",
    )
    list_filter = ("purpose", "status")
    search_fields = (
        "user__email",
        "external_reference",
        "provider_reference",
        "mpesa_transaction_code",
    )
    readonly_fields = tuple(field.name for field in Payment._meta.fields)

    def changelist_view(self, request, extra_context=None):
        now = timezone.localtime(timezone.now())
        today = now.date()
        start_today = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        start_tomorrow = start_today + timedelta(days=1)
        start_yesterday = start_today - timedelta(days=1)

        start_week = start_today - timedelta(days=today.weekday())
        start_last_week = start_week - timedelta(days=7)
        start_month = start_today.replace(day=1)
        start_last_month = (start_month - timedelta(days=1)).replace(day=1)
        start_next_month = (
            start_month.replace(year=start_month.year + 1, month=1)
            if start_month.month == 12
            else start_month.replace(month=start_month.month + 1)
        )
        start_year = start_today.replace(month=1, day=1)
        start_next_year = start_year.replace(year=start_year.year + 1)

        periods = {
            "today": (start_today, start_tomorrow),
            "yesterday": (start_yesterday, start_today),
            "this_week": (start_week, start_week + timedelta(days=7)),
            "last_week": (start_last_week, start_week),
            "this_month": (start_month, start_next_month),
            "last_month": (start_last_month, start_month),
            "this_year": (start_year, start_next_year),
        }

        analytics = {}
        successful_payments = Payment.objects.filter(status=PaymentStatus.SUCCESS)
        for name, (start, end) in periods.items():
            summary = successful_payments.filter(
                completed_at__gte=start,
                completed_at__lt=end,
            ).aggregate(
                income_usd=Sum("amount_usd"),
                income_kes=Sum("amount_kes"),
                transactions=Count("id"),
            )
            analytics[name] = {
                "income_usd": summary["income_usd"] or Decimal("0.00"),
                "income_kes": summary["income_kes"] or 0,
                "transactions": summary["transactions"] or 0,
            }

        context = {
            **(extra_context or {}),
            "finance_analytics": analytics,
            "finance_timezone": timezone.get_current_timezone_name(),
        }
        return super().changelist_view(request, extra_context=context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
