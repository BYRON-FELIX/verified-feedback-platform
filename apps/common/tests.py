from types import SimpleNamespace

from django.apps import apps
from django.contrib import admin
from django.db.models.deletion import PROTECT
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User
from apps.geo.models import Country
from apps.common.admin import PlatformSettingsAdmin
from apps.common.models import PlatformSettings
from apps.common.services import task_access_lock_reason
from apps.payments.admin import PaymentAdmin
from apps.payments.models import Payment, PaymentPurpose
from apps.reviewers.models import ReviewerProfile
from apps.wallets.admin import WalletTransactionAdmin
from apps.wallets.models import TransactionType, WalletTransaction
from apps.wallets.services import get_or_create_wallet
from apps.withdrawals.admin import WithdrawalAdmin
from apps.withdrawals.models import Withdrawal, WithdrawalProvider


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


class ProtectedRelationDeletionTests(TestCase):
    def test_no_model_relation_blocks_parent_deletion(self):
        protected_fields = [
            f"{model._meta.label}.{field.name}"
            for model in apps.get_models()
            for field in model._meta.get_fields()
            if field.concrete
            and field.is_relation
            and getattr(field.remote_field, "on_delete", None) is PROTECT
        ]

        self.assertEqual(protected_fields, [])

    def test_deleting_user_removes_financial_records(self):
        user = User.objects.create_user(email="delete-me@example.com", password="test-password")
        wallet = get_or_create_wallet(user)
        transaction = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=TransactionType.ADJUSTMENT,
            amount=10,
            balance_after=10,
        )
        withdrawal = Withdrawal.objects.create(
            wallet=wallet,
            user=user,
            amount=10,
            net_amount=10,
            provider=WithdrawalProvider.MPESA,
            idempotency_key="delete-me-withdrawal",
        )
        payment = Payment.objects.create(
            user=user,
            purpose=PaymentPurpose.STKPUSH_TEST,
            amount_usd=1,
            amount_kes=100,
            external_reference="delete-me-payment",
        )

        user.delete()

        self.assertFalse(WalletTransaction.objects.filter(pk=transaction.pk).exists())
        self.assertFalse(Withdrawal.objects.filter(pk=withdrawal.pk).exists())
        self.assertFalse(Payment.objects.filter(pk=payment.pk).exists())

    def test_deleting_country_preserves_reviewer_profile(self):
        user = User.objects.create_user(
            email="country-reviewer@example.com",
            password="test-password",
        )
        country = Country.objects.create(code="ZZ", name="Test country")
        profile = ReviewerProfile.objects.create(user=user, country=country)

        country.delete()

        profile.refresh_from_db()
        self.assertIsNone(profile.country)


class AdminSiteAccessTests(TestCase):
    def test_admin_dashboard_opens_site_campaign_browser(self):
        admin_user = User.objects.create_user(
            email="site-admin@example.com",
            password="test-password",
            role="ADMIN",
        )
        client = Client()
        client.force_login(admin_user)

        response = client.get(reverse("dashboard"), secure=True)

        self.assertRedirects(
            response,
            reverse("campaigns:reviewer_list"),
            fetch_redirect_response=False,
        )
        site_response = client.get(response.url, secure=True)
        self.assertEqual(site_response.status_code, 200)
        self.assertContains(site_response, "Find tasks worth your time.")
        self.assertContains(site_response, "Django admin")

    def test_admin_can_open_public_homepage(self):
        admin_user = User.objects.create_user(
            email="homepage-admin@example.com",
            password="test-password",
            role="ADMIN",
        )
        client = Client()
        client.force_login(admin_user)

        response = client.get("/", secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your experience")

    def test_superuser_dashboard_also_opens_site_campaign_browser(self):
        superuser = User.objects.create_superuser(
            email="site-superuser@example.com",
            password="test-password",
        )
        client = Client()
        client.force_login(superuser)

        response = client.get(reverse("dashboard"), secure=True)

        self.assertRedirects(
            response,
            reverse("campaigns:reviewer_list"),
            fetch_redirect_response=False,
        )
