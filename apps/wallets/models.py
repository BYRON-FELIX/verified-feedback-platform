import uuid

from django.conf import settings
from django.db import models


class TransactionType(models.TextChoices):
    TASK_REWARD = "TASK_REWARD", "Task reward"
    WITHDRAWAL = "WITHDRAWAL", "Withdrawal"
    WITHDRAWAL_REVERSAL = "WITHDRAWAL_REVERSAL", "Withdrawal reversal"
    PHONE_VERIFICATION_DEPOSIT = "PHONE_VERIFICATION_DEPOSIT", "Phone verification deposit"
    PREMIUM_UNLOCK = "PREMIUM_UNLOCK", "Premium unlock"
    REFUND = "REFUND", "Refund"
    ADJUSTMENT = "ADJUSTMENT", "Adjustment"
    BONUS = "BONUS", "Bonus"
    FEE = "FEE", "Fee"


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lifetime_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lifetime_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(available_balance__gte=0),
                name="wallet_available_nonneg",
            ),
            models.CheckConstraint(
                condition=models.Q(pending_balance__gte=0),
                name="wallet_pending_nonneg",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} — ${self.available_balance}"


class WalletTransaction(models.Model):
    """
    Append-only ledger. Source of truth for a wallet's balance.
    Never update or delete rows here.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=32, choices=TransactionType.choices)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Signed USD: positive = credit, negative = debit.",
    )
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    description = models.CharField(max_length=240, blank=True)
    idempotency_key = models.CharField(max_length=80, blank=True, null=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "-created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.amount >= 0 else ""
        return f"{sign}{self.amount} {self.transaction_type} → {self.wallet.user.email}"