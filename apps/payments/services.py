import base64
import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.models import PlatformSettings
from apps.common.services import surveys_are_locked
from apps.notifications.services import notify
from apps.geo.models import Country
from apps.reviewers.models import ReviewerProfile

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


def has_successful_mpesa_verification(user):
    return Payment.objects.filter(
        user=user,
        purpose=PaymentPurpose.MPESA_ACCOUNT_VERIFICATION,
        status=PaymentStatus.SUCCESS,
    ).exists()


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


def process_callback(payload):
    reference = payload.get("external_reference") or payload.get("reference")
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
    provider_reference = (
        payload.get("reference")
        or payment.provider_reference
        or payment.external_reference
    )
    status_response = _payhero_request(
        "GET",
        "/api/v2/transaction-status",
        query={"reference": provider_reference},
    )
    status = str(status_response.get("status", payload.get("status", ""))).upper()
    provider_reference = str(
        status_response.get("provider_reference")
        or status_response.get("third_party_reference")
        or payment.provider_reference
    )

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == PaymentStatus.SUCCESS:
            return payment
        payment.provider_response = status_response
        payment.provider_reference = provider_reference
        if status == "SUCCESS":
            if payment.purpose == PaymentPurpose.MPESA_ACCOUNT_VERIFICATION:
                payment.user.is_phone_verified = True
                payment.user.save(update_fields=["is_phone_verified", "updated_at"])
            else:
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
                "provider_response",
            ])
            notify(
                user=payment.user,
                type=(
                    "SURVEY_UNLOCK_PAYMENT_COMPLETED"
                    if payment.purpose == PaymentPurpose.SURVEY_UNLOCK
                    else "MPESA_ACCOUNT_VERIFIED"
                ),
                title=(
                    "Survey access unlocked"
                    if payment.purpose == PaymentPurpose.SURVEY_UNLOCK
                    else "M-Pesa account verified"
                ),
                body=(
                    "Your survey access is now unlocked."
                    if payment.purpose == PaymentPurpose.SURVEY_UNLOCK
                    else "Your M-Pesa account is verified. You can now request M-Pesa withdrawals."
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
