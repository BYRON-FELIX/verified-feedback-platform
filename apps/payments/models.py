import uuid

from django.conf import settings
from django.db import models


class PaymentPurpose(models.TextChoices):
    SURVEY_UNLOCK = "SURVEY_UNLOCK", "Survey unlock"
    MPESA_ACCOUNT_VERIFICATION = "MPESA_ACCOUNT_VERIFICATION", "M-Pesa account verification"
    STKPUSH_TEST = "STKPUSH_TEST", "STK push test"


class PaymentStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    SUCCESS = "SUCCESS", "Successful"
    FAILED = "FAILED", "Failed"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    purpose = models.CharField(max_length=32, choices=PaymentPurpose.choices)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2)
    amount_kes = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.QUEUED,
    )
    external_reference = models.CharField(max_length=80, unique=True)
    provider_reference = models.CharField(max_length=100, blank=True)
    mpesa_transaction_code = models.CharField(
        max_length=40,
        blank=True,
        help_text="M-Pesa receipt/transaction code returned by PayHero.",
    )
    checkout_request_id = models.CharField(max_length=100, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "purpose", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} — ${self.amount_usd} ({self.get_status_display()})"
