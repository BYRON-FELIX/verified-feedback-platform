import uuid

from django.conf import settings
from django.db import models

from apps.wallets.models import Wallet


class WithdrawalStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    REVERSED = "REVERSED", "Reversed"
    CANCELLED = "CANCELLED", "Cancelled"


class WithdrawalProvider(models.TextChoices):
    MPESA = "MPESA", "M-Pesa"
    PAYPAL = "PAYPAL", "PayPal"
    CARD = "CARD", "Card"
    MANUAL = "MANUAL", "Manual"


class Withdrawal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="withdrawals")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="withdrawals",
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_withheld = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(
        max_length=16, choices=WithdrawalStatus.choices, default=WithdrawalStatus.PENDING
    )
    provider = models.CharField(
        max_length=16, choices=WithdrawalProvider.choices, default=WithdrawalProvider.MPESA
    )
    destination_phone = models.CharField(max_length=20, blank=True)
    destination_email = models.EmailField(blank=True)

    provider_reference = models.CharField(max_length=80, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    idempotency_key = models.CharField(max_length=80, unique=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="processed_withdrawals",
    )

    class Meta:
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "-requested_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="withdrawal_amount_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(net_amount__gt=0),
                name="withdrawal_net_positive",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} — ${self.amount} ({self.status})"