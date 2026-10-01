from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User
from apps.geo.models import Country
from apps.reviewers.forms import ReviewerProfileForm
from apps.reviewers.models import ReviewerProfile

from .models import Payment, PaymentPurpose, PaymentStatus
from .services import PayHeroError, has_successful_mpesa_verification, process_callback


class PaymentCallbackVerificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="payment-reviewer@example.com",
            password="test-password",
            first_name="Payment",
            last_name="Reviewer",
            phone_number="+254700000001",
        )
        self.payment = Payment.objects.create(
            user=self.user,
            purpose=PaymentPurpose.MPESA_ACCOUNT_VERIFICATION,
            amount_usd="1.00",
            amount_kes=100,
            phone_number=self.user.phone_number,
            external_reference="verification-payment-ref",
            provider_reference="payhero-provider-ref",
        )

    def test_profile_phone_change_invalidates_existing_phone_verification(self):
        self.user.is_phone_verified = True
        self.user.save(update_fields=["is_phone_verified"])
        country = Country.objects.create(code="ZZ", name="Test country")
        profile = ReviewerProfile.objects.create(user=self.user, country=country)
        form = ReviewerProfileForm(
            data={
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "phone_number": "+254700000002",
                "country": str(country.pk),
                "date_of_birth": "",
                "bio": "",
                "preferred_categories": [],
            },
            instance=profile,
            user=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_phone_verified)
        self.assertEqual(self.user.phone_number, "+254700000002")

    @patch("apps.payments.services._payhero_request")
    def test_success_uses_stored_reference_and_provider_amount(self, payhero_request):
        payhero_request.return_value = {
            "status": "SUCCESS",
            "external_reference": self.payment.external_reference,
            "amount": self.payment.amount_kes,
            "mpesa_receipt_number": "QWE123",
        }

        process_callback({
            "external_reference": self.payment.external_reference,
            "reference": "unrelated-provider-reference",
            "status": "FAILED",
        })

        payhero_request.assert_called_once_with(
            "GET",
            "/api/v2/transaction-status",
            query={"reference": self.payment.provider_reference},
        )
        self.payment.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.SUCCESS)
        self.assertTrue(self.user.is_phone_verified)
        self.assertTrue(has_successful_mpesa_verification(self.user))

    @patch("apps.payments.services._payhero_request")
    def test_callback_status_cannot_confirm_a_payment(self, payhero_request):
        payhero_request.return_value = {}

        with self.assertRaises(PayHeroError):
            process_callback({
                "external_reference": self.payment.external_reference,
                "status": "SUCCESS",
            })

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.QUEUED)

    @patch("apps.payments.services._payhero_request")
    def test_success_without_provider_amount_cannot_confirm_payment(self, payhero_request):
        payhero_request.return_value = {
            "status": "SUCCESS",
            "external_reference": self.payment.external_reference,
        }

        with self.assertRaises(PayHeroError):
            process_callback({"external_reference": self.payment.external_reference})

        self.payment.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.QUEUED)
        self.assertFalse(self.user.is_phone_verified)

    @patch("apps.payments.services._payhero_request")
    def test_mismatched_provider_amount_cannot_confirm_payment(self, payhero_request):
        payhero_request.return_value = {
            "status": "SUCCESS",
            "external_reference": self.payment.external_reference,
            "amount": 1,
        }

        with self.assertRaises(PayHeroError):
            process_callback({"external_reference": self.payment.external_reference})

        self.payment.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.QUEUED)
        self.assertFalse(self.user.is_phone_verified)

    @patch("apps.payments.services._payhero_request")
    def test_changed_phone_does_not_receive_verification_from_old_prompt(self, payhero_request):
        self.user.phone_number = "+254700000002"
        self.user.save(update_fields=["phone_number"])
        payhero_request.return_value = {
            "status": "SUCCESS",
            "external_reference": self.payment.external_reference,
            "amount": self.payment.amount_kes,
        }

        process_callback({"external_reference": self.payment.external_reference})

        self.payment.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.SUCCESS)
        self.assertFalse(self.user.is_phone_verified)
        self.assertFalse(has_successful_mpesa_verification(self.user))

    @patch("apps.payments.services._payhero_request")
    def test_mismatched_provider_reference_cannot_confirm_payment(self, payhero_request):
        payhero_request.return_value = {
            "status": "SUCCESS",
            "external_reference": "another-payment",
            "amount": self.payment.amount_kes,
        }

        with self.assertRaises(PayHeroError):
            process_callback({"external_reference": self.payment.external_reference})

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.QUEUED)
