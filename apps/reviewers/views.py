from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, render

from apps.common.decorators import reviewer_required
from apps.common.services import (
    get_platform_settings,
    requires_account_verification,
    surveys_are_locked,
)
from apps.geo.models import Country
from apps.submissions.models import Submission
from apps.wallets.services import get_or_create_wallet

from .forms import ReviewerProfileForm, StyledPasswordChangeForm
from .models import ReviewerProfile


@reviewer_required
def dashboard(request):
    wallet = get_or_create_wallet(request.user)
    submission_count = Submission.objects.filter(reviewer=request.user).count()
    context = {
        "page_title": "Dashboard",
        "nav_active": "dashboard",
        "wallet": wallet,
        "submission_count": submission_count,
        "requires_account_verification": requires_account_verification(request.user, wallet),
        "surveys_locked": surveys_are_locked(request.user, wallet),
        "platform_settings": get_platform_settings(),
    }
    return render(request, "reviewer/dashboard.html", context)


@reviewer_required
def profile(request):
    default_country = Country.objects.filter(is_active=True).first()
    profile, _ = ReviewerProfile.objects.get_or_create(
        user=request.user,
        defaults={"country": default_country},
    )

    if request.method == "POST":
        form = ReviewerProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("reviewers:profile")
    else:
        form = ReviewerProfileForm(instance=profile, user=request.user)

    # Stats for the sidebar card
    wallet = get_or_create_wallet(request.user)
    submission_count = Submission.objects.filter(reviewer=request.user).count()

    return render(request, "reviewer/profile.html", {
        "page_title": "Profile",
        "nav_active": "profile",
        "form": form,
        "profile": profile,
        "wallet": wallet,
        "submission_count": submission_count,
        "referred_count": request.user.referred_users.count(),
        "referral_verified_count": request.user.referred_users.filter(is_phone_verified=True).count(),
    })


@reviewer_required
def change_password(request):
    if request.method == "POST":
        form = StyledPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated.")
            return redirect("reviewers:profile")
    else:
        form = StyledPasswordChangeForm(request.user)
    return render(request, "reviewer/change_password.html", {
        "page_title": "Change password",
        "nav_active": "profile",
        "form": form,
    })