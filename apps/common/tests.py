from types import SimpleNamespace

from django.contrib import admin
from django.test import TestCase

from apps.accounts.models import User
from apps.common.admin import PlatformSettingsAdmin
from apps.common.models import PlatformSettings
from apps.common.services import task_access_lock_reason
from apps.payments.admin import PaymentAdmin
from apps.payments.models import Payment
from apps.wallets.admin import WalletTransactionAdmin
from apps.wallets.models import WalletTransaction
from apps.wallets.services import get_or_create_wallet
from apps.withdrawals.admin import WithdrawalAdmin
from apps.withdrawals.models import Withdrawal


class TaskAccessLockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="reviewer@example.com", password="test")
        self.wallet = get_or_create_wallet(self.user)
        self.settings = PlatformSettings.get_solo()

    def test_phone_verification_locks_tasks_at_configured_threshold(self):
        self.wallet.lifetime_earnings = self.settings.verification_trigger_usd
        self.wallet.save(update_fields=["lifetime_earnings"])

        self.assertEqual(task_access_lock_reason(self.user, self.wallet), "account_verification")

        self.user.is_phone_verified = True
        self.user.save(update_fields=["is_phone_verified"])
        self.assertIsNone(task_access_lock_reason(self.user, self.wallet))

    def test_premium_upgrade_locks_tasks_at_configured_threshold(self):
        self.user.is_phone_verified = True
        self.user.save(update_fields=["is_phone_verified"])
        self.wallet.lifetime_earnings = self.settings.premium_unlock_trigger_usd
        self.wallet.save(update_fields=["lifetime_earnings"])

        self.assertEqual(task_access_lock_reason(self.user, self.wallet), "premium_upgrade")

    def test_phone_verification_requirement_takes_priority_when_both_locks_apply(self):
        self.wallet.lifetime_earnings = self.settings.premium_unlock_trigger_usd
        self.wallet.save(update_fields=["lifetime_earnings"])

        self.assertEqual(task_access_lock_reason(self.user, self.wallet), "account_verification")


class SuperuserDeletePermissionTests(TestCase):
    admin_models = (
        (PlatformSettingsAdmin, PlatformSettings),
        (PaymentAdmin, Payment),
        (WalletTransactionAdmin, WalletTransaction),
        (WithdrawalAdmin, Withdrawal),
    )

    def test_superuser_can_delete_protected_admin_records(self):
        request = SimpleNamespace(user=SimpleNamespace(is_superuser=True))

        for admin_class, model in self.admin_models:
            with self.subTest(model=model.__name__):
                model_admin = admin_class(model, admin.site)
                self.assertTrue(model_admin.has_delete_permission(request))

    def test_non_superuser_cannot_delete_protected_admin_records(self):
        request = SimpleNamespace(user=SimpleNamespace(is_superuser=False))

        for admin_class, model in self.admin_models:
            with self.subTest(model=model.__name__):
                model_admin = admin_class(model, admin.site)
                self.assertFalse(model_admin.has_delete_permission(request))
