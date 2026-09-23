from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class PlatformSettings(models.Model):
    """Admin-managed thresholds for reviewer account and survey access."""

    verification_trigger_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("30.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Lifetime earnings at which the reviewer must verify their account.",
    )
    premium_unlock_trigger_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("80.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Lifetime earnings at which surveys are locked until unlocked.",
    )
    premium_unlock_cost_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("20.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="One-time wallet debit required to unlock surveys.",
    )
    mpesa_account_verification_fee_usd = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="One-time PayHero fee required before M-Pesa withdrawals.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Platform settings"
        verbose_name_plural = "Platform settings"

    def __str__(self):
        return "Platform settings"

    @classmethod
    def get_solo(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings
