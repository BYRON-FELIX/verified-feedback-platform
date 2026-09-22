from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.notifications.services import notify
from apps.wallets.models import TransactionType
from apps.wallets.services import debit, get_or_create_wallet

from .models import Withdrawal, WithdrawalStatus


class WithdrawalError(Exception):
    pass


MIN_WITHDRAWAL_KSH = Decimal("50.00")


@transaction.atomic
def request_withdrawal(*, user, amount, destination_phone):
    """
    Creates a PENDING withdrawal. Does NOT debit the wallet yet —
    the debit happens on COMPLETED.
    """
    amount = Decimal(str(amount))
    if amount < MIN_WITHDRAWAL_KSH:
        raise WithdrawalError(f"Minimum withdrawal is KSh {MIN_WITHDRAWAL_KSH}.")

    wallet = get_or_create_wallet(user)

    # Re-lock and re-check
    from apps.wallets.models import Wallet
    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

    if wallet.available_balance_ksh < amount:
        raise WithdrawalError("Insufficient available balance.")

    active = Withdrawal.objects.filter(
        user=user,
        status__in=[WithdrawalStatus.PENDING, WithdrawalStatus.PROCESSING],
    ).exists()
    if active:
        raise WithdrawalError("You already have a withdrawal in progress.")

    tax_pct = Decimal(str(getattr(settings, "WITHHOLDING_TAX_PERCENTAGE", "0")))
    tax = (amount * tax_pct / Decimal("100")).quantize(Decimal("0.01"))
    fee = Decimal("0.00")
    net = amount - tax - fee

    if net <= 0:
        raise WithdrawalError("Net amount must be greater than zero.")

    withdrawal = Withdrawal.objects.create(
        wallet=wallet,
        user=user,
        amount_ksh=amount,
        fee_ksh=fee,
        tax_withheld_ksh=tax,
        net_amount_ksh=net,
        destination_phone=destination_phone,
        idempotency_key=f"wd-{user.id}-{timezone.now().timestamp()}",
    )

    notify(
        user=user,
        type="WITHDRAWAL_REQUESTED",
        title="Withdrawal requested",
        body=f"Your withdrawal of KSh {amount} is now pending review.",
    )
    return withdrawal


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

    # Debit the wallet — this is the moment money actually leaves the user's balance.
    debit(
        user=w.user,
        amount=w.amount_ksh,
        transaction_type=TransactionType.WITHDRAWAL,
        description=f"Withdrawal to {w.destination_phone}",
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
        body=f"KSh {w.net_amount_ksh} has been sent to {w.destination_phone}.",
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