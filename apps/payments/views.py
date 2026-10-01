import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.common.decorators import admin_required, reviewer_required

from .services import (
    PayHeroError,
    initiate_mpesa_account_verification,
    initiate_stkpush_test,
    initiate_survey_unlock,
    process_callback,
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
    return redirect("reviewers:dashboard")


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
    return redirect("reviewers:dashboard")


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
