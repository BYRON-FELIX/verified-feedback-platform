import base64
import json
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.models import PlatformSettings
from apps.common.services import surveys_are_locked
from apps.notifications.services import notify
from apps.geo.models import Country
from apps.reviewers.models import ReviewerProfile
from apps.wallets.services import credit, get_or_create_wallet
from apps.wallets.models import TransactionType

from .models import Payment, PaymentPurpose, PaymentStatus


class PayHeroError(Exception):
    pass


def _auth_header():
    token = getattr(settings, "PAYHERO_AUTH_TOKEN", "")
    if token:
        return f"Basic {token}" if not token.lower().startswith("basic ") else token

    username = getattr(settings, "PAYHERO_API_KEY", "")
    password = getattr(settings, "PAYHERO_API_SECRET", "")
    if not username or not password:
        raise PayHeroError("PayHero credentials are not configured.")
    encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {encoded}"


def _payhero_request(method, path, *, payload=None, query=None):
    url = f"{settings.PAYHERO_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urlencode(query)}"
    body = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": _auth_header(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=settings.PAYHERO_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise PayHeroError("PayHero request failed.") from exc


def _amount_kes(amount_usd):
    return int(
        (Decimal(str(amount_usd)) * settings.KSH_PER_USD).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def _callback_url():
    if not settings.PAYHERO_CALLBACK_BASE_URL:
        raise PayHeroError("PayHero callback URL is not configured.")
    return f"{settings.PAYHERO_CALLBACK_BASE_URL.rstrip('/')}/payments/payhero/callback/"


def _mpesa_transaction_code(response):
    """Find the customer-facing M-Pesa receipt in PayHero's response payload."""
    receipt_keys = (
        "mpesa_receipt_number",
        "mpesa_receipt",
        "transaction_code",
        "receipt_number",
        "receipt_no",
        "receipt",
        "transactionCode",
        "third_party_reference",
        "payment_reference",
        "transaction_reference",
        "provider_reference",
    )
    normalized_keys = [
        "".join(character for character in key.lower() if character.isalnum())
        for key in receipt_keys
    ]
    objects = [response]
    candidates = []
    while objects:
        current = objects.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                normalized_key = "".join(
                    character for character in str(key).lower() if character.isalnum()
                )
                if normalized_key in normalized_keys and value:
                    if not isinstance(value, (dict, list)):
                        candidates.append((normalized_key, str(value)))
                if str(key).lower() in {"key", "name"} and isinstance(value, str):
                    continue
                objects.append(value)
            case_insensitive = {
                str(key).lower(): value
                for key, value in current.items()
            }
            if "key" in case_insensitive and "value" in case_insensitive:
                label = "".join(
                    character
                    for character in str(case_insensitive["key"]).lower()
                    if character.isalnum()
                )
                pair_value = case_insensitive["value"]
                if label in normalized_keys and pair_value:
                    candidates.append((label, str(pair_value)))
        elif isinstance(current, list):
            objects.extend(current)

    for key in normalized_keys:
        for candidate_key, value in candidates:
            if candidate_key == key:
                return value
    return ""


def _award_referral_bonus(referred_user):
    inviter = referred_user.referred_by
    if not inviter or inviter.pk == referred_user.pk:
        return

    get_or_create_wallet(inviter)
    credit(
        user=inviter,
        amount=Decimal("5.00"),
        transaction_type=TransactionType.BONUS,
        description=f"Referral bonus for {referred_user.display_name}",
        reference_type="Referral",
        reference_id=referred_user.pk,
        idempotency_key=f"referral-bonus-{referred_user.pk}",
    )


def has_successful_mpesa_verification(user):
    if not user.phone_number:
        return False
    return Payment.objects.filter(
        user=user,
        purpose=PaymentPurpose.MPESA_ACCOUNT_VERIFICATION,
        status=PaymentStatus.SUCCESS,
        phone_number=user.phone_number,
    ).exists()


def get_user_payment(*, user, payment_id):
    try:
        payment_uuid = UUID(str(payment_id))
    except (AttributeError, TypeError, ValueError):
        return None
    return Payment.objects.filter(pk=payment_uuid, user=user).first()


def initiate_mpesa_account_verification(*, user):
    if has_successful_mpesa_verification(user):
        raise PayHeroError("Your M-Pesa account is already verified.")
    if not user.phone_number:
        raise PayHeroError("Add your phone number before verifying M-Pesa.")
    if settings.PAYHERO_CHANNEL_ID <= 0:
        raise PayHeroError("PayHero payment channel is not configured.")
    if Payment.objects.filter(
        user=user,
        purpose=PaymentPurpose.MPESA_ACCOUNT_VERIFICATION,
        status=PaymentStatus.QUEUED,
    ).exists():
        raise PayHeroError("Your M-Pesa verification payment is already in progress.")

    config = PlatformSettings.get_solo()
    payment = Payment.objects.create(
        user=user,
        purpose=PaymentPurpose.MPESA_ACCOUNT_VERIFICATION,
        amount_usd=config.mpesa_account_verification_fee_usd,
        amount_kes=_amount_kes(config.mpesa_account_verification_fee_usd),
        phone_number=user.phone_number,
        external_reference=f"mpesa-verification-{uuid.uuid4().hex[:36]}",
    )
    try:
        response = _payhero_request(
            "POST",
            "/api/v2/payments",
            payload={
                "amount": payment.amount_kes,
                "phone_number": user.phone_number,
                "channel_id": settings.PAYHERO_CHANNEL_ID,
                "provider": "m-pesa",
                "external_reference": payment.external_reference,
                "customer_name": user.get_full_name() or user.email,
                "callback_url": _callback_url(),
            },
        )
    except PayHeroError as exc:
        Payment.objects.filter(pk=payment.pk).update(
            status=PaymentStatus.FAILED,
            failure_reason=str(exc),
        )
        raise

    Payment.objects.filter(pk=payment.pk).update(
        provider_reference=str(response.get("reference", "")),
        checkout_request_id=str(response.get("CheckoutRequestID", "")),
        provider_response=response,
    )
    payment.refresh_from_db()
    notify(
        user=user,
        type="MPESA_VERIFICATION_PAYMENT_STARTED",
        title="M-Pesa verification payment started",
        body=f"PayHero sent an M-Pesa prompt for KSh {payment.amount_kes}. "
             "Enter your PIN to verify your account.",
    )
    return payment


def initiate_survey_unlock(*, user):
    from apps.wallets.services import get_or_create_wallet

    wallet = get_or_create_wallet(user)
    if not surveys_are_locked(user, wallet):
        raise PayHeroError("Survey access is already unlocked.")

    if not user.phone_number:
        raise PayHeroError("Add a phone number before starting payment.")
    if settings.PAYHERO_CHANNEL_ID <= 0:
        raise PayHeroError("PayHero payment channel is not configured.")
    if Payment.objects.filter(
        user=user,
        purpose=PaymentPurpose.SURVEY_UNLOCK,
        status=PaymentStatus.QUEUED,
    ).exists():
        raise PayHeroError("You already have a survey unlock payment in progress.")

    config = PlatformSettings.get_solo()
    with transaction.atomic():
        payment = Payment.objects.create(
            user=user,
            purpose=PaymentPurpose.SURVEY_UNLOCK,
            amount_usd=config.premium_unlock_cost_usd,
            amount_kes=_amount_kes(config.premium_unlock_cost_usd),
            phone_number=user.phone_number,
            external_reference=f"survey-unlock-{uuid.uuid4().hex[:40]}",
        )
    try:
        response = _payhero_request(
            "POST",
            "/api/v2/payments",
            payload={
                "amount": payment.amount_kes,
                "phone_number": user.phone_number,
                "channel_id": settings.PAYHERO_CHANNEL_ID,
                "provider": "m-pesa",
                "external_reference": payment.external_reference,
                "customer_name": user.get_full_name() or user.email,
                "callback_url": _callback_url(),
            },
        )
    except PayHeroError as exc:
        Payment.objects.filter(pk=payment.pk).update(
            status=PaymentStatus.FAILED,
            failure_reason=str(exc),
        )
        raise

    Payment.objects.filter(pk=payment.pk).update(
        provider_reference=str(response.get("reference", "")),
        checkout_request_id=str(response.get("CheckoutRequestID", "")),
        provider_response=response,
    )
    payment.refresh_from_db()
    return payment


def initiate_stkpush_test(*, user, phone_number, amount_kes):
    """Send a PayHero prompt for manual integration testing."""
    if settings.PAYHERO_CHANNEL_ID <= 0:
        raise PayHeroError("PayHero payment channel is not configured.")
    if amount_kes < 1:
        raise PayHeroError("Amount must be at least KSh 1.")

    payment = Payment.objects.create(
        user=user,
        purpose=PaymentPurpose.STKPUSH_TEST,
        amount_usd=(Decimal(amount_kes) / settings.KSH_PER_USD).quantize(Decimal("0.01")),
        amount_kes=amount_kes,
        phone_number=phone_number,
        external_reference=f"stkpush-test-{uuid.uuid4().hex[:40]}",
    )
    try:
        response = _payhero_request(
            "POST",
            "/api/v2/payments",
            payload={
                "amount": payment.amount_kes,
                "phone_number": phone_number,
                "channel_id": settings.PAYHERO_CHANNEL_ID,
                "provider": "m-pesa",
                "external_reference": payment.external_reference,
                "customer_name": user.get_full_name() or user.email,
                "callback_url": _callback_url(),
            },
        )
    except PayHeroError as exc:
        Payment.objects.filter(pk=payment.pk).update(
            status=PaymentStatus.FAILED,
            failure_reason=str(exc),
        )
        raise

    Payment.objects.filter(pk=payment.pk).update(
        provider_reference=str(response.get("reference", "")),
        checkout_request_id=str(response.get("CheckoutRequestID", "")),
        provider_response=response,
    )
    payment.refresh_from_db()
    return payment


def process_callback(payload):
    if not isinstance(payload, dict):
        raise PayHeroError("PayHero callback payload is invalid.")

    callback_response = payload.get("response")
    if callback_response is not None and not isinstance(callback_response, dict):
        raise PayHeroError("PayHero callback response is invalid.")
    callback_response = callback_response or {}
    reference = (
        payload.get("external_reference")
        or callback_response.get("ExternalReference")
        or callback_response.get("external_reference")
        or payload.get("reference")
    )
    if not reference:
        raise PayHeroError("PayHero callback has no reference.")

    payment = Payment.objects.filter(
        external_reference=reference,
    ).first()
    if not payment:
        payment = Payment.objects.filter(
            provider_reference=reference,
        ).first()
    if not payment:
        raise PayHeroError("Unknown PayHero payment reference.")
    return refresh_payment_status(payment, callback_response=callback_response)


def refresh_payment_status(payment, *, callback_response=None):
    if payment.status in (PaymentStatus.SUCCESS, PaymentStatus.FAILED):
        return payment

    provider_reference = payment.provider_reference or payment.external_reference
    status_response = _payhero_request(
        "GET",
        "/api/v2/transaction-status",
        query={"reference": provider_reference},
    )
    if not isinstance(status_response, dict):
        raise PayHeroError("PayHero transaction status response is invalid.")
    status_value = status_response.get("status")
    if not status_value:
        raise PayHeroError("PayHero transaction status response has no status.")
    provider_status = str(status_value).strip().upper()
    if provider_status not in {"QUEUED", "SUCCESS", "FAILED"}:
        raise PayHeroError("PayHero transaction status response has an unknown status.")
    if status_response.get("success") is False:
        raise PayHeroError("PayHero could not retrieve the transaction status.")
    status = provider_status

    expected_references = {
        payment.external_reference,
        payment.provider_reference,
    } - {""}
    for key in (
        "external_reference",
        "externalReference",
        "ExternalReference",
        "merchant_reference",
    ):
        response_reference = status_response.get(key)
        if response_reference and str(response_reference) not in expected_references:
            raise PayHeroError("PayHero transaction status reference does not match payment.")

    response_amount = next(
        (
            status_response[key]
            for key in ("amount", "amount_kes", "transaction_amount", "paid_amount")
            if status_response.get(key) is not None
        ),
        None,
    )
    if response_amount is not None:
        try:
            amount_matches = Decimal(str(response_amount)) == Decimal(payment.amount_kes)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise PayHeroError("PayHero transaction status has an invalid amount.") from exc
        if not amount_matches:
            raise PayHeroError("PayHero transaction amount does not match payment.")

    if callback_response:
        callback_amount = callback_response.get("Amount", callback_response.get("amount"))
        if callback_amount is not None:
            try:
                callback_amount_matches = (
                    Decimal(str(callback_amount)) == Decimal(payment.amount_kes)
                )
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise PayHeroError("PayHero callback has an invalid payment amount.") from exc
            if not callback_amount_matches:
                raise PayHeroError("PayHero callback amount does not match payment.")

    provider_reference = str(
        status_response.get("provider_reference")
        or status_response.get("third_party_reference")
        or payment.provider_reference
        or payment.external_reference
    )
    mpesa_transaction_code = (
        _mpesa_transaction_code(callback_response or {})
        or _mpesa_transaction_code(status_response)
    )

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status in (PaymentStatus.SUCCESS, PaymentStatus.FAILED):
            return payment
        payment.provider_response = status_response
        payment.provider_reference = provider_reference
        if status == "SUCCESS":
            payment.mpesa_transaction_code = (
                mpesa_transaction_code or payment.mpesa_transaction_code
            )
            phone_matches = (
                payment.purpose != PaymentPurpose.MPESA_ACCOUNT_VERIFICATION
                or (
                    payment.phone_number
                    and payment.phone_number == payment.user.phone_number
                )
            )
            if (
                payment.purpose == PaymentPurpose.MPESA_ACCOUNT_VERIFICATION
                and phone_matches
            ):
                payment.user.is_phone_verified = True
                payment.user.save(update_fields=["is_phone_verified", "updated_at"])
                _award_referral_bonus(payment.user)
            elif payment.purpose == PaymentPurpose.SURVEY_UNLOCK:
                default_country = Country.objects.filter(is_active=True).first()
                profile, _ = ReviewerProfile.objects.get_or_create(
                    user=payment.user,
                    defaults={"country": default_country},
                )
                profile.premium_unlocked_at = timezone.now()
                profile.save(update_fields=["premium_unlocked_at", "updated_at"])
            payment.status = PaymentStatus.SUCCESS
            payment.completed_at = timezone.now()
            payment.save(update_fields=[
                "status",
                "completed_at",
                "provider_reference",
                "mpesa_transaction_code",
                "provider_response",
            ])
            if payment.purpose != PaymentPurpose.STKPUSH_TEST:
                verification_not_granted = (
                    payment.purpose == PaymentPurpose.MPESA_ACCOUNT_VERIFICATION
                    and not phone_matches
                )
                notify(
                    user=payment.user,
                    type=(
                        "SURVEY_UNLOCK_PAYMENT_COMPLETED"
                        if payment.purpose == PaymentPurpose.SURVEY_UNLOCK
                        else (
                            "MPESA_ACCOUNT_VERIFICATION_PHONE_CHANGED"
                            if verification_not_granted
                            else "MPESA_ACCOUNT_VERIFIED"
                        )
                    ),
                    title=(
                        "Survey access unlocked"
                        if payment.purpose == PaymentPurpose.SURVEY_UNLOCK
                        else (
                            "Payment received; phone verification incomplete"
                            if verification_not_granted
                            else "M-Pesa account verified"
                        )
                    ),
                    body=(
                        "Your survey access is now unlocked."
                        if payment.purpose == PaymentPurpose.SURVEY_UNLOCK
                        else (
                            "The phone number on your account changed after this prompt "
                            "was sent. Complete M-Pesa verification again for your current number."
                            if verification_not_granted
                            else (
                                "Your M-Pesa account is verified. "
                                "You can now request M-Pesa withdrawals."
                                + (
                                    f" Transaction code: {payment.mpesa_transaction_code}."
                                    if payment.mpesa_transaction_code
                                    else ""
                                )
                            )
                        )
                    ),
                )
        elif status == "FAILED":
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = str(
                status_response.get("error_message") or "PayHero payment failed."
            )
            payment.save(update_fields=[
                "status",
                "failure_reason",
                "provider_reference",
                "provider_response",
            ])
            if payment.purpose != PaymentPurpose.STKPUSH_TEST:
                notify(
                    user=payment.user,
                    type="MPESA_VERIFICATION_PAYMENT_FAILED"
                    if payment.purpose == PaymentPurpose.MPESA_ACCOUNT_VERIFICATION
                    else "SURVEY_UNLOCK_PAYMENT_FAILED",
                    title="Payment failed",
                    body=payment.failure_reason,
                )
        else:
            payment.save(update_fields=["provider_reference", "provider_response"])
        return payment
