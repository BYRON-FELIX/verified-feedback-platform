from django.test import TestCase

from apps.accounts.models import User
from apps.common.models import PlatformSettings
from apps.common.services import task_access_lock_reason
from apps.wallets.services import get_or_create_wallet


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
