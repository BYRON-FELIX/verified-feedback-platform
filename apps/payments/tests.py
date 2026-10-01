from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import User, UserRole
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
    def test_documented_status_response_without_amount_confirms_payment(self, payhero_request):
        payhero_request.return_value = {
            "success": True,
            "status": "SUCCESS",
            "payment_reference": "",
            "third_party_reference": "SKQ96C7K7H",
            "reference": "6b71cb8b-638d-4b6e-9c7c-b0334a641e3a",
            "CheckoutRequestID": "",
            "provider_reference": "SKQ96C7K7H",
        }

        process_callback({"external_reference": self.payment.external_reference})

        self.payment.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.SUCCESS)
        self.assertTrue(self.user.is_phone_verified)
        self.assertEqual(self.payment.provider_reference, "SKQ96C7K7H")

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

    @patch("apps.payments.services._payhero_request")
    def test_completed_stk_push_saves_transaction_code(self, payhero_request):
        self.payment.purpose = PaymentPurpose.STKPUSH_TEST
        self.payment.save(update_fields=["purpose"])
        payhero_request.return_value = {
            "status": "SUCCESS",
            "external_reference": self.payment.external_reference,
            "amount": self.payment.amount_kes,
            "transaction_code": "RCP456",
        }

        process_callback({"external_reference": self.payment.external_reference})

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.SUCCESS)
        self.assertEqual(self.payment.mpesa_transaction_code, "RCP456")

    @patch("apps.payments.services._payhero_request")
    def test_nested_mpesa_receipt_is_saved_for_completed_payment(self, payhero_request):
        self.payment.purpose = PaymentPurpose.STKPUSH_TEST
        self.payment.save(update_fields=["purpose"])
        payhero_request.return_value = {
            "status": "SUCCESS",
            "external_reference": self.payment.external_reference,
            "amount": self.payment.amount_kes,
            "data": {
                "ResultParameter": [
                    {"Key": "MpesaReceiptNumber", "Value": "NESTED123"},
                ],
            },
        }

        process_callback({"external_reference": self.payment.external_reference})

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.mpesa_transaction_code, "NESTED123")

    @patch("apps.payments.services._payhero_request")
    def test_documented_callback_and_transaction_status_formats(self, payhero_request):
        payhero_request.return_value = {
            "transaction_date": "2024-11-26T08:41:14.160604Z",
            "provider": "m-pesa",
            "success": True,
            "merchant": "PayHero",
            "payment_reference": "",
            "third_party_reference": "SKQ96C7K7H",
            "status": "SUCCESS",
            "reference": "6b71cb8b-638d-4b6e-9c7c-b0334a641e3a",
            "CheckoutRequestID": "",
            "provider_reference": "SKQ96C7K7H",
        }

        process_callback({
            "forward_url": "",
            "response": {
                "Amount": self.payment.amount_kes,
                "CheckoutRequestID": "ws_CO_14012024103543427709099876",
                "ExternalReference": self.payment.external_reference,
                "MerchantRequestID": "3202-70921557-1",
                "MpesaReceiptNumber": "SAE3YULR0Y",
                "Phone": self.payment.phone_number,
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "Status": "Success",
            },
            "status": True,
        })

        self.payment.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.SUCCESS)
        self.assertEqual(self.payment.mpesa_transaction_code, "SAE3YULR0Y")
        self.assertTrue(self.user.is_phone_verified)

    @patch("apps.payments.services._payhero_request")
    def test_only_documented_payment_statuses_are_accepted(self, payhero_request):
        payhero_request.return_value = {
            "success": True,
            "status": "COMPLETED",
        }

        with self.assertRaises(PayHeroError):
            process_callback({"external_reference": self.payment.external_reference})

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.QUEUED)

    @patch("apps.payments.services._payhero_request")
    def test_failed_payment_is_terminal_and_not_polled_again(self, payhero_request):
        payhero_request.return_value = {
            "status": "FAILED",
            "external_reference": self.payment.external_reference,
            "error_message": "Cancelled by user",
        }

        process_callback({"external_reference": self.payment.external_reference})
        process_callback({"external_reference": self.payment.external_reference})

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.FAILED)
        self.assertEqual(payhero_request.call_count, 1)

    @patch("apps.payments.services._payhero_request")
    def test_authenticated_status_poll_returns_terminal_result(self, payhero_request):
        payhero_request.return_value = {
            "status": "SUCCESS",
            "external_reference": self.payment.external_reference,
            "amount": self.payment.amount_kes,
            "mpesa_receipt_number": "ABC789",
        }
        client = Client()
        client.force_login(self.user)

        response = client.get(
            reverse("payments:status", args=[self.payment.pk]),
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], PaymentStatus.SUCCESS)
        self.assertEqual(response.json()["mpesa_transaction_code"], "ABC789")

    def test_users_cannot_poll_another_users_payment(self):
        other_user = User.objects.create_user(
            email="other-reviewer@example.com",
            password="test-password",
            role=UserRole.REVIEWER,
        )
        client = Client()
        client.force_login(other_user)

        response = client.get(
            reverse("payments:status", args=[self.payment.pk]),
            secure=True,
        )

        self.assertEqual(response.status_code, 404)

    @patch("apps.payments.views.initiate_stkpush_test")
    def test_polling_ui_uses_three_second_interval_and_ten_attempt_limit(self, initiate):
        admin = User.objects.create_superuser(
            email="payment-admin@example.com",
            password="test-password",
        )
        client = Client()
        client.force_login(admin)
        initiate.return_value = self.payment

        response = client.post(
            reverse("payments:stkpush_test"),
            {"phone_number": "+254700000001", "amount_kes": "100"},
            secure=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "window.setTimeout(pollPayment, 3000)")
        self.assertContains(response, "const maxPolls = 10")
