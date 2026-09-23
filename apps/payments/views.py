import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.common.decorators import reviewer_required

from .services import PayHeroError, initiate_survey_unlock, process_callback


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


@csrf_exempt
@require_POST
def payhero_callback(request):
    try:
        payload = json.loads(request.body.decode() or "{}")
        process_callback(payload)
    except (json.JSONDecodeError, PayHeroError):
        return JsonResponse({"received": False}, status=400)
    return JsonResponse({"received": True})
