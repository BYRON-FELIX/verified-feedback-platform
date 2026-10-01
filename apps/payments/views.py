import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.common.decorators import admin_required, reviewer_required

from .services import (
    PayHeroError,
    initiate_mpesa_account_verification,
    initiate_stkpush_test,
    initiate_survey_unlock,
    get_user_payment,
    process_callback,
    refresh_payment_status,
)


@reviewer_required
@require_POST
def start_mpesa_account_verification(request):
    try:
        payment = initiate_mpesa_account_verification(user=request.user)
    except PayHeroError as exc:
        messages.error(request, str(exc))
        return redirect("reviewers:dashboard")

    messages.info(
        request,
        f"An M-Pesa verification prompt for KSh {payment.amount_kes} was sent to your phone. "
        "Enter your PIN to complete account verification.",
    )
    return redirect(f"{reverse('reviewers:dashboard')}?payment_id={payment.pk}")


@reviewer_required
@require_POST
def start_survey_unlock(request):
    try:
        payment = initiate_survey_unlock(user=request.user)
    except PayHeroError as exc:
        messages.error(request, str(exc))
        return redirect("reviewers:dashboard")

    messages.info(
        request,
        f"PayHero sent an M-Pesa prompt for KSh {payment.amount_kes}. "
        "Enter your PIN to complete the unlock.",
    )
    return redirect(f"{reverse('reviewers:dashboard')}?payment_id={payment.pk}")


@admin_required
def stkpush_test(request):
    context = {"page_title": "PayHero STK push test", "payment": None}
    if request.method == "POST":
        phone_number = request.POST.get("phone_number", "").strip()
        try:
            amount_kes = int(request.POST.get("amount_kes", "0"))
            if not phone_number:
                raise PayHeroError("Enter an M-Pesa phone number.")
            payment = initiate_stkpush_test(
                user=request.user,
                phone_number=phone_number,
                amount_kes=amount_kes,
            )
        except (PayHeroError, TypeError, ValueError) as exc:
            context["error"] = str(exc)
        else:
            context["payment"] = payment
            messages.success(
                request,
                f"STK prompt sent to {phone_number} for KSh {payment.amount_kes}.",
            )
    return render(request, "payments/stkpush_test.html", context)


@csrf_exempt
@require_POST
def payhero_callback(request):
    try:
        payload = json.loads(request.body.decode() or "{}")
        process_callback(payload)
    except (json.JSONDecodeError, PayHeroError):
        return JsonResponse({"received": False}, status=400)
    return JsonResponse({"received": True})


@login_required
@require_GET
def payment_status(request, payment_id):
    payment = get_user_payment(user=request.user, payment_id=payment_id)
    if payment is None:
        raise Http404("Payment not found.")
    try:
        payment = refresh_payment_status(payment)
    except PayHeroError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse({
        "status": payment.status,
        "status_display": payment.get_status_display(),
        "mpesa_transaction_code": payment.mpesa_transaction_code,
        "failure_reason": payment.failure_reason,
    })
