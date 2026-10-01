from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.common.decorators import admin_required, reviewer_required
from apps.common.models import PlatformSettings
from apps.payments.services import (
    PayHeroError,
    has_successful_mpesa_verification,
    initiate_mpesa_account_verification,
)
from apps.wallets.services import get_or_create_wallet

from .forms import WithdrawalRequestForm
from .models import Withdrawal, WithdrawalProvider, WithdrawalStatus
from .services import (
    WithdrawalError,
    mark_completed,
    mark_failed,
    mark_processing,
    request_withdrawal,
    validate_withdrawal_provider,
)


def _user_country_code(user):
    try:
        if hasattr(user, "reviewer_profile") and user.reviewer_profile.country:
            return user.reviewer_profile.country.code
    except Exception:
        pass
    return None


# ---------- Reviewer ----------

@reviewer_required
def wallet_view(request):
    wallet = get_or_create_wallet(request.user)
    transactions = wallet.transactions.order_by("-created_at")[:50]
    withdrawals = Withdrawal.objects.filter(user=request.user).order_by("-requested_at")[:10]

    return render(request, "reviewer/wallet.html", {
        "page_title": "Wallet",
        "nav_active": "wallet",
        "wallet": wallet,
        "transactions": transactions,
        "withdrawals": withdrawals,
    })


@reviewer_required
def request_withdrawal_view(request):
    wallet = get_or_create_wallet(request.user)
    country_code = _user_country_code(request.user)

    if request.method == "POST":
        form = WithdrawalRequestForm(request.POST)
        if form.is_valid():
            try:
                provider = form.cleaned_data["provider"]
                validate_withdrawal_provider(provider, country_code)
                if (
                    provider == WithdrawalProvider.MPESA
                    and not has_successful_mpesa_verification(request.user)
                ):
                    initiate_mpesa_account_verification(user=request.user)
                    messages.info(
                        request,
                        "An M-Pesa verification prompt was sent to your phone. "
                        "Complete it, then return here to submit your withdrawal.",
                    )
                    return redirect("withdrawals:request")
                w = request_withdrawal(
                    user=request.user,
                    amount=form.cleaned_data["amount"],
                    provider=provider,
                    destination_phone=form.cleaned_data.get("destination_phone") or "",
                    destination_email=form.cleaned_data.get("destination_email") or "",
                )
                messages.success(request, f"Withdrawal request for ${w.amount} submitted.")
                return redirect("withdrawals:detail", pk=w.pk)
            except (PayHeroError, WithdrawalError) as e:
                messages.error(request, str(e))
    else:
        initial = {}
        if request.user.phone_number:
            initial["destination_phone"] = request.user.phone_number
        if country_code == "KE":
            initial["provider"] = WithdrawalProvider.MPESA
        elif country_code:
            initial["provider"] = WithdrawalProvider.PAYPAL
        form = WithdrawalRequestForm(initial=initial)

    return render(request, "reviewer/withdrawal_request.html", {
        "page_title": "Request withdrawal",
        "nav_active": "wallet",
        "wallet": wallet,
        "form": form,
        "min_amount": settings.MIN_WITHDRAWAL_USD,
        "user_country_code": country_code,
        "mpesa_fee": PlatformSettings.get_solo().mpesa_account_verification_fee_usd,
        "mpesa_verified": has_successful_mpesa_verification(request.user),
        "country_code": country_code or "",
    })


@reviewer_required
def withdrawal_list(request):
    withdrawals = Withdrawal.objects.filter(user=request.user).order_by("-requested_at")
    return render(request, "reviewer/withdrawal_list.html", {
        "page_title": "Withdrawals",
        "nav_active": "wallet",
        "withdrawals": withdrawals,
    })


@reviewer_required
def withdrawal_detail(request, pk):
    withdrawal = get_object_or_404(Withdrawal, pk=pk, user=request.user)
    return render(request, "reviewer/withdrawal_detail.html", {
        "page_title": "Withdrawal",
        "nav_active": "wallet",
        "withdrawal": withdrawal,
    })


# ---------- Admin ----------

@admin_required
def admin_withdrawal_queue(request):
    pending = Withdrawal.objects.filter(
        status__in=[WithdrawalStatus.PENDING, WithdrawalStatus.PROCESSING]
    ).select_related("user").order_by("requested_at")

    recent = Withdrawal.objects.filter(
        status__in=[WithdrawalStatus.COMPLETED, WithdrawalStatus.FAILED, WithdrawalStatus.REVERSED]
    ).select_related("user").order_by("-requested_at")[:25]

    return render(request, "admin_panel/withdrawal_queue.html", {
        "page_title": "Withdrawal queue",
        "pending": pending,
        "recent": recent,
    })


@admin_required
@require_POST
def admin_withdrawal_action(request, pk, action):
    get_object_or_404(Withdrawal, pk=pk)
    try:
        if action == "processing":
            mark_processing(withdrawal_id=pk, admin_user=request.user)
            messages.success(request, "Marked as processing.")
        elif action == "complete":
            mark_completed(withdrawal_id=pk, admin_user=request.user)
            messages.success(request, "Marked as completed and wallet debited.")
        elif action == "fail":
            reason = request.POST.get("reason", "Payment failed.")
            mark_failed(withdrawal_id=pk, admin_user=request.user, reason=reason)
            messages.success(request, "Marked as failed.")
        else:
            messages.error(request, f"Unknown action: {action}")
            return redirect("withdrawals:admin_queue")
    except WithdrawalError as e:
        messages.error(request, str(e))
    return redirect("withdrawals:admin_queue")