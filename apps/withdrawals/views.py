from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.common.decorators import admin_required, reviewer_required
from apps.wallets.services import get_or_create_wallet

from .forms import WithdrawalRequestForm
from .models import Withdrawal, WithdrawalStatus
from .services import WithdrawalError, mark_completed, mark_failed, mark_processing, request_withdrawal


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

    if request.method == "POST":
        form = WithdrawalRequestForm(request.POST)
        if form.is_valid():
            try:
                w = request_withdrawal(
                    user=request.user,
                    amount=form.cleaned_data["amount_ksh"],
                    destination_phone=form.cleaned_data["destination_phone"],
                )
                messages.success(request, f"Withdrawal request for KSh {w.amount_ksh} submitted.")
                return redirect("withdrawals:detail", pk=w.pk)
            except WithdrawalError as e:
                messages.error(request, str(e))
    else:
        initial = {}
        if request.user.phone_number:
            initial["destination_phone"] = request.user.phone_number
        form = WithdrawalRequestForm(initial=initial)

    return render(request, "reviewer/withdrawal_request.html", {
        "page_title": "Request withdrawal",
        "nav_active": "wallet",
        "wallet": wallet,
        "form": form,
        "min_amount": 50,
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
def admin_withdrawal_action(request, pk, action):
    withdrawal = get_object_or_404(Withdrawal, pk=pk)
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