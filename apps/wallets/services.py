from decimal import Decimal

from django.db import transaction

from .models import TransactionType, Wallet, WalletTransaction


class InsufficientBalance(Exception):
    pass


def get_or_create_wallet(user) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


@transaction.atomic
def credit(
    *,
    user,
    amount,
    transaction_type,
    description="",
    reference_type="",
    reference_id=None,
    idempotency_key=None,
) -> WalletTransaction:
    """
    Credit a user's wallet. Always goes through the ledger.
    Returns the created WalletTransaction.
    """
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("Credit amount must be > 0.")

    if idempotency_key:
        existing = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing

    # Lock the wallet row
    wallet = Wallet.objects.select_for_update().get(user=user)

    new_available = wallet.available_balance_ksh + amount
    new_lifetime = wallet.lifetime_earnings_ksh + amount

    wallet.available_balance_ksh = new_available
    wallet.lifetime_earnings_ksh = new_lifetime
    wallet.save(update_fields=["available_balance_ksh", "lifetime_earnings_ksh", "updated_at"])

    return WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=transaction_type,
        amount_ksh=amount,
        balance_after_ksh=new_available,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        idempotency_key=idempotency_key,
    )


@transaction.atomic
def debit(
    *,
    user,
    amount,
    transaction_type,
    description="",
    reference_type="",
    reference_id=None,
    idempotency_key=None,
) -> WalletTransaction:
    """
    Debit a user's wallet. Raises InsufficientBalance if balance would go negative.
    """
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError("Debit amount must be > 0.")

    if idempotency_key:
        existing = WalletTransaction.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing

    wallet = Wallet.objects.select_for_update().get(user=user)

    if wallet.available_balance_ksh < amount:
        raise InsufficientBalance(
            f"Wallet balance {wallet.available_balance_ksh} is less than debit {amount}."
        )

    new_available = wallet.available_balance_ksh - amount
    wallet.available_balance_ksh = new_available
    wallet.lifetime_withdrawn_ksh = wallet.lifetime_withdrawn_ksh + amount
    wallet.save(update_fields=["available_balance_ksh", "lifetime_withdrawn_ksh", "updated_at"])

    return WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type=transaction_type,
        amount_ksh=-amount,
        balance_after_ksh=new_available,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        idempotency_key=idempotency_key,
    )