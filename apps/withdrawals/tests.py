from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User
from apps.wallets.models import TransactionType, WalletTransaction
from apps.wallets.services import get_or_create_wallet

from .models import WithdrawalProvider, WithdrawalStatus
from .services import (
    mark_completed,
    mark_failed,
    request_withdrawal,
    validate_withdrawal_provider,
    WithdrawalError,
)


class WithdrawalFundsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="reviewer@example.com", password="test")
        self.wallet = get_or_create_wallet(self.user)
        self.wallet.available_balance = Decimal("150.00")
        self.wallet.save(update_fields=["available_balance"])

    @patch("apps.withdrawals.services.notify")
    def test_request_debits_balance_immediately(self, notify):
        withdrawal = request_withdrawal(
            user=self.user,
            amount=Decimal("100.00"),
            provider=WithdrawalProvider.PAYPAL,
            destination_email="reviewer@example.com",
        )

        self.wallet.refresh_from_db()
        self.assertEqual(withdrawal.status, WithdrawalStatus.PENDING)
        self.assertEqual(self.wallet.available_balance, Decimal("50.00"))
        self.assertEqual(
            WalletTransaction.objects.get(
                idempotency_key=f"withdrawal-debit-{withdrawal.id}",
            ).amount,
            Decimal("-100.00"),
        )

    @patch("apps.withdrawals.services.notify")
    def test_failed_withdrawal_refunds_reserved_balance(self, notify):
        withdrawal = request_withdrawal(
            user=self.user,
            amount=Decimal("100.00"),
            provider=WithdrawalProvider.PAYPAL,
            destination_email="reviewer@example.com",
        )

        mark_failed(
            withdrawal_id=withdrawal.id,
            admin_user=self.user,
            reason="Payout failed",
        )

        self.wallet.refresh_from_db()
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, WithdrawalStatus.FAILED)
        self.assertEqual(self.wallet.available_balance, Decimal("150.00"))
        self.assertEqual(
            WalletTransaction.objects.get(
                idempotency_key=f"withdrawal-refund-{withdrawal.id}",
            ).transaction_type,
            TransactionType.WITHDRAWAL_REVERSAL,
        )

    @patch("apps.withdrawals.services.notify")
    def test_completion_does_not_debit_twice(self, notify):
        withdrawal = request_withdrawal(
            user=self.user,
            amount=Decimal("100.00"),
            provider=WithdrawalProvider.PAYPAL,
            destination_email="reviewer@example.com",
        )

        mark_completed(withdrawal_id=withdrawal.id, admin_user=self.user)

        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.available_balance, Decimal("50.00"))
        self.assertEqual(self.wallet.lifetime_withdrawn, Decimal("100.00"))
        self.assertEqual(
            WalletTransaction.objects.filter(
                idempotency_key=f"withdrawal-debit-{withdrawal.id}",
            ).count(),
            1,
        )

    def test_country_rejects_disallowed_withdrawal_methods(self):
        with self.assertRaisesMessage(WithdrawalError, "Only M-Pesa"):
            validate_withdrawal_provider(WithdrawalProvider.PAYPAL, "KE")
        with self.assertRaisesMessage(WithdrawalError, "M-Pesa withdrawals are not available"):
            validate_withdrawal_provider(WithdrawalProvider.MPESA, "US")
