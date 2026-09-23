from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.models import PlatformSettings
from apps.notifications.services import notify
from apps.payments.services import has_successful_mpesa_verification
from apps.wallets.models import TransactionType, Wallet
from apps.wallets.services import debit, get_or_create_wallet

from .models import Withdrawal, WithdrawalProvider, WithdrawalStatus


class WithdrawalError(Exception):
    pass


@transaction.atomic
def request_withdrawal(*, user, amount, provider, destination_phone="", destination_email=""):
    """
    Creates a PENDING withdrawal. Debits the wallet only on COMPLETED.
    """
    amount = Decimal(str(amount))
    min_amount = settings.MIN_WITHDRAWAL_USD

    if amount < min_amount:
        raise WithdrawalError(f"Minimum withdrawal is ${min_amount}.")

    wallet = get_or_create_wallet(user)
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

    if wallet.available_balance < amount:
        raise WithdrawalError("Insufficient available balance.")

    active = Withdrawal.objects.filter(
        user=user,
        status__in=[WithdrawalStatus.PENDING, WithdrawalStatus.PROCESSING],
    ).exists()
    if active:
        raise WithdrawalError("You already have a withdrawal in progress.")

    # Country-based provider enforcement
    country_code = _user_country_code(user)
    if country_code == "KE" and provider != WithdrawalProvider.MPESA:
        raise WithdrawalError("Only M-Pesa is available in your country.")
    if country_code != "KE" and provider == WithdrawalProvider.MPESA:
        raise WithdrawalError("M-Pesa is not available in your country.")

    # Provider-specific validation
    if provider == WithdrawalProvider.MPESA:
        if not destination_phone:
            raise WithdrawalError("A phone number is required for M-Pesa.")
        if not has_successful_mpesa_verification(user):
            fee = PlatformSettings.get_solo().mpesa_account_verification_fee_usd
            raise WithdrawalError(
                f"Complete the M-Pesa account verification payment of ${fee} "
                "before requesting an M-Pesa withdrawal."
            )
    else:
        if not destination_email:
            raise WithdrawalError("An email address is required for PayPal or card.")

    # Fees
    fee = Decimal("0.00")

    tax_pct = Decimal(str(getattr(settings, "WITHHOLDING_TAX_PERCENTAGE", "0")))
    tax = (amount * tax_pct / Decimal("100")).quantize(Decimal("0.01"))

    net = amount - tax - fee
    if net <= 0:
        raise WithdrawalError(
            f"After fees (${fee}) and tax (${tax}), the net amount would be zero or negative. "
            f"Please request a larger amount."
        )

    withdrawal = Withdrawal.objects.create(
        wallet=wallet,
        user=user,
        amount=amount,
        fee=fee,
        tax_withheld=tax,
        net_amount=net,
        provider=provider,
        destination_phone=destination_phone or "",
        destination_email=destination_email or "",
        idempotency_key=f"wd-{user.id}-{timezone.now().timestamp()}",
    )

    notify(
        user=user,
        type="WITHDRAWAL_REQUESTED",
        title="Withdrawal requested",
        body=(
            f"Your {withdrawal.get_provider_display()} withdrawal of ${amount} "
            "is now pending review. No additional verification fee is required."
            if provider != WithdrawalProvider.MPESA
            else f"Your M-Pesa withdrawal of ${amount} is now pending review."
        ),
    )
    return withdrawal


def _user_country_code(user):
    """Best-effort country code detection. Returns None if unknown."""
    try:
        if hasattr(user, "reviewer_profile") and user.reviewer_profile.country:
            return user.reviewer_profile.country.code
    except Exception:
        pass
    try:
        if hasattr(user, "country") and user.country:
            return user.country.code
    except Exception:
        pass
    return None


@transaction.atomic
def mark_processing(*, withdrawal_id, admin_user):
    w = Withdrawal.objects.select_for_update().get(pk=withdrawal_id)
    if w.status != WithdrawalStatus.PENDING:
        raise WithdrawalError(f"Cannot move {w.status} → PROCESSING.")
    w.status = WithdrawalStatus.PROCESSING
    w.processed_at = timezone.now()
    w.processed_by = admin_user
    w.save(update_fields=["status", "processed_at", "processed_by"])
    return w


@transaction.atomic
def mark_completed(*, withdrawal_id, admin_user, provider_reference="", provider_response=None):
    w = Withdrawal.objects.select_for_update().get(pk=withdrawal_id)
    if w.status not in (WithdrawalStatus.PENDING, WithdrawalStatus.PROCESSING):
        raise WithdrawalError(f"Cannot complete from status {w.status}.")

    debit(
        user=w.user,
        amount=w.amount,
        transaction_type=TransactionType.WITHDRAWAL,
        description=f"Withdrawal via {w.get_provider_display()}",
        reference_type="Withdrawal",
        reference_id=w.id,
        idempotency_key=f"withdrawal-debit-{w.id}",
    )

    w.status = WithdrawalStatus.COMPLETED
    w.completed_at = timezone.now()
    w.processed_by = admin_user
    w.provider_reference = provider_reference or w.provider_reference
    if provider_response:
        w.provider_response = provider_response
    w.save(update_fields=[
        "status", "completed_at", "processed_by",
        "provider_reference", "provider_response",
    ])

    notify(
        user=w.user,
        type="WITHDRAWAL_COMPLETED",
        title="Withdrawal completed",
        body=f"${w.net_amount} has been sent via {w.get_provider_display()}.",
    )
    return w


@transaction.atomic
def mark_failed(*, withdrawal_id, admin_user, reason):
    w = Withdrawal.objects.select_for_update().get(pk=withdrawal_id)
    if w.status not in (WithdrawalStatus.PENDING, WithdrawalStatus.PROCESSING):
        raise WithdrawalError(f"Cannot fail from status {w.status}.")
    w.status = WithdrawalStatus.FAILED
    w.failure_reason = reason
    w.processed_by = admin_user
    w.save(update_fields=["status", "failure_reason", "processed_by"])
    notify(
        user=w.user,
        type="WITHDRAWAL_FAILED",
        title="Withdrawal failed",
        body=f"Your withdrawal could not be completed: {reason}",
    )
    return w


@transaction.atomic
def cancel_by_user(*, withdrawal_id, user):
    w = Withdrawal.objects.select_for_update().get(pk=withdrawal_id, user=user)
    if w.status != WithdrawalStatus.PENDING:
        raise WithdrawalError("Only pending withdrawals can be cancelled.")
    w.status = WithdrawalStatus.CANCELLED
    w.save(update_fields=["status"])
    return w