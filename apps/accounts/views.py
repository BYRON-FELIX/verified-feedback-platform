from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.urls import reverse
from django.shortcuts import redirect, render

from .forms import BusinessSignupForm, ReviewerSignupForm
from apps.wallets.models import TransactionType, WalletTransaction


REFERRAL_SESSION_KEY = "signup_referral_code"


def _referral_signup_data(request):
    referral_code = request.GET.get("ref", "").strip().upper()
    if referral_code:
        request.session[REFERRAL_SESSION_KEY] = referral_code
    return {"referral_code": referral_code or request.session.get(REFERRAL_SESSION_KEY, "")}


def _signup_post_data(request):
    post_data = request.POST.copy()
    if not post_data.get("referral_code"):
        post_data["referral_code"] = request.session.get(REFERRAL_SESSION_KEY, "")
    return post_data


def _clear_signup_referral(request):
    request.session.pop(REFERRAL_SESSION_KEY, None)


def reviewer_signup(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        form = ReviewerSignupForm(_signup_post_data(request))
        if form.is_valid():
            user = form.save()
            _clear_signup_referral(request)
            # Ensure profile exists
            from apps.reviewers.models import ReviewerProfile
            ReviewerProfile.objects.get_or_create(
                user=user,
                defaults={"country": form.cleaned_data["country"]},
            )
            login(request, user)
            messages.success(request, "Welcome! Your reviewer account is ready.")
            return redirect("/dashboard/")
    else:
        form = ReviewerSignupForm(initial=_referral_signup_data(request))
    return render(request, "auth/signup_reviewer.html", {"form": form})


def business_signup(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        form = BusinessSignupForm(_signup_post_data(request))
        if form.is_valid():
            user = form.save()
            _clear_signup_referral(request)
            login(request, user)
            messages.success(request, "Welcome! Your business account is ready.")
            return redirect("/")
    else:
        form = BusinessSignupForm(initial=_referral_signup_data(request))
    return render(request, "auth/signup_business.html", {"form": form})


@login_required
def referrals(request):
    referred_users = request.user.referred_users.order_by("-created_at")
    referral_bonus_transactions = WalletTransaction.objects.filter(
        wallet__user=request.user,
        transaction_type=TransactionType.BONUS,
        reference_type="Referral",
    )
    return render(request, "accounts/referrals.html", {
        "page_title": "Referrals",
        "nav_active": "referrals",
        "referred_users": referred_users,
        "referred_count": referred_users.count(),
        "verified_count": referred_users.filter(is_phone_verified=True).count(),
        "bonus_total": referral_bonus_transactions.aggregate(total=Sum("amount"))["total"] or 0,
        "referral_link": request.build_absolute_uri(
            f"{reverse('accounts:signup_reviewer')}?ref={request.user.referral_code}"
        ),
    })