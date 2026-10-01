from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.common.decorators import business_required, reviewer_required
from apps.common.services import get_platform_settings, surveys_are_locked, task_access_lock_reason
from apps.wallets.services import get_or_create_wallet

from .forms import CampaignForm, QuestionFormSet, RequirementFormSet
from .models import (
    ApplicationStatus,
    Campaign,
    CampaignApplication,
    CampaignStatus,
    Category,
)


# ---------- Business: manage own campaigns ----------

@business_required
def business_campaign_list(request):
    business = request.user.owned_businesses.first()
    campaigns = Campaign.objects.none()
    if business:
        campaigns = Campaign.objects.filter(business=business).order_by("-created_at")
    return render(request, "business/campaigns_list.html", {
        "page_title": "Campaigns",
        "nav_active": "campaigns",
        "business": business,
        "campaigns": campaigns,
    })


@business_required
def business_campaign_create(request):
    business = request.user.owned_businesses.first()

    if not business:
        messages.warning(
            request,
            "You need a business profile before creating campaigns. Complete it first.",
        )
        return redirect("/business/profile/")

    if request.method == "POST":
        form = CampaignForm(request.POST)
        req_formset = RequirementFormSet(request.POST, prefix="req")
        q_formset = QuestionFormSet(request.POST, prefix="q")

        if form.is_valid() and req_formset.is_valid() and q_formset.is_valid():
            with transaction.atomic():
                campaign = form.save(commit=False)
                campaign.business = business
                campaign.status = CampaignStatus.DRAFT
                campaign.budget_total = (
                    campaign.reward_amount * campaign.target_participants
                )
                campaign.save()

                req_formset.instance = campaign
                req_formset.save()

                q_formset.instance = campaign
                q_formset.save()

            messages.success(request, "Campaign saved as draft.")
            return redirect("campaigns:business_detail", pk=campaign.pk)
    else:
        form = CampaignForm()
        req_formset = RequirementFormSet(prefix="req")
        q_formset = QuestionFormSet(prefix="q")

    return render(request, "business/campaign_form.html", {
        "page_title": "New Campaign",
        "nav_active": "campaigns",
        "form": form,
        "req_formset": req_formset,
        "q_formset": q_formset,
        "is_create": True,
    })


@business_required
def business_campaign_detail(request, pk):
    business = request.user.owned_businesses.first()
    campaign = get_object_or_404(Campaign, pk=pk, business=business)

    applications = (
        campaign.applications
        .select_related("reviewer")
        .order_by("-applied_at")
    )

    return render(request, "business/campaign_detail.html", {
        "page_title": campaign.title,
        "nav_active": "campaigns",
        "campaign": campaign,
        "applications": applications,
    })


@business_required
@require_POST
def business_application_reject(request, pk):
    business = request.user.owned_businesses.first()
    if not business:
        messages.error(request, "No business profile.")
        return redirect("/business/")

    with transaction.atomic():
        application = (
            CampaignApplication.objects
            .select_for_update()
            .select_related("campaign")
            .filter(pk=pk, campaign__business=business)
            .first()
        )
        if not application:
            messages.error(request, "Application not found.")
            return redirect("/campaigns/business/")

        if application.status != ApplicationStatus.ACCEPTED:
            messages.warning(request, "Only accepted applications can be rejected.")
            return redirect("campaigns:business_detail", pk=application.campaign.pk)

        campaign = Campaign.objects.select_for_update().get(pk=application.campaign.pk)
        application.status = ApplicationStatus.REJECTED
        application.rejected_at = timezone.now()
        application.save(update_fields=["status", "rejected_at"])

        if campaign.filled_slots > 0:
            campaign.filled_slots -= 1
            campaign.save(update_fields=["filled_slots"])

    messages.success(request, "Application rejected. Slot released.")
    return redirect("campaigns:business_detail", pk=campaign.pk)


# ---------- Reviewer: browse & view ----------

def reviewer_campaign_list(request):
    """
    Public list of active campaigns.
    Anonymous users can browse; applying requires login.
    """
    campaigns = (
        Campaign.objects.filter(status=CampaignStatus.ACTIVE)
        .select_related("business", "category", "county")
        .order_by("-created_at")
    )

    category_id = request.GET.get("category")
    if category_id:
        campaigns = campaigns.filter(category_id=category_id)

    search = request.GET.get("q")
    if search:
        campaigns = campaigns.filter(title__icontains=search)

    categories = Category.objects.filter(is_active=True)

    applied_ids = set()
    surveys_locked = False
    phone_verification_required = False
    if request.user.is_authenticated and request.user.role == "REVIEWER":
        wallet = get_or_create_wallet(request.user)
        surveys_locked = surveys_are_locked(
            request.user,
            wallet,
        )
        phone_verification_required = (
            task_access_lock_reason(request.user, wallet) == "account_verification"
        )
        applied_ids = set(
            CampaignApplication.objects
            .filter(reviewer=request.user)
            .values_list("campaign_id", flat=True)
        )

    return render(request, "reviewer/campaigns_list.html", {
        "page_title": "Find Tasks",
        "nav_active": "campaigns",
        "campaigns": campaigns,
        "categories": categories,
        "selected_category": category_id,
        "search": search,
        "applied_ids": applied_ids,
        "is_public_browse": not request.user.is_authenticated,
        "surveys_locked": surveys_locked,
        "phone_verification_required": phone_verification_required,
        "platform_settings": get_platform_settings(),
    })


def reviewer_campaign_detail(request, slug):
    campaign = get_object_or_404(
        Campaign.objects.select_related("business", "category", "county"),
        slug=slug,
    )

    existing = None
    surveys_locked = False
    phone_verification_required = False
    if request.user.is_authenticated and request.user.role == "REVIEWER":
        wallet = get_or_create_wallet(request.user)
        surveys_locked = surveys_are_locked(
            request.user,
            wallet,
        )
        phone_verification_required = (
            task_access_lock_reason(request.user, wallet) == "account_verification"
        )
        existing = CampaignApplication.objects.filter(
            campaign=campaign, reviewer=request.user
        ).first()

    return render(request, "reviewer/campaign_detail.html", {
        "page_title": campaign.title,
        "nav_active": "campaigns",
        "campaign": campaign,
        "existing_application": existing,
        "surveys_locked": surveys_locked,
        "phone_verification_required": phone_verification_required,
        "platform_settings": get_platform_settings(),
    })


@reviewer_required
def reviewer_campaign_apply(request, slug):
    if request.method != "POST":
        return redirect("campaigns:reviewer_detail", slug=slug)

    with transaction.atomic():
        campaign = (
            Campaign.objects
            .select_for_update()
            .filter(slug=slug)
            .first()
        )
        if not campaign:
            messages.error(request, "Campaign not found.")
            return redirect("campaigns:reviewer_list")

        if campaign.status != CampaignStatus.ACTIVE:
            messages.error(request, "This campaign is not currently accepting applications.")
            return redirect("campaigns:reviewer_detail", slug=slug)

        if campaign.filled_slots >= campaign.target_participants:
            messages.error(request, "This campaign is full.")
            return redirect("campaigns:reviewer_detail", slug=slug)

        if CampaignApplication.objects.filter(
            campaign=campaign, reviewer=request.user
        ).exists():
            messages.info(request, "You have already applied to this campaign.")
            return redirect("campaigns:reviewer_detail", slug=slug)

        CampaignApplication.objects.create(
            campaign=campaign,
            reviewer=request.user,
            status=ApplicationStatus.ACCEPTED,
            accepted_at=timezone.now(),
        )

        campaign.filled_slots += 1
        campaign.save(update_fields=["filled_slots"])

    lock_reason = task_access_lock_reason(
        request.user,
        get_or_create_wallet(request.user),
    )
    if lock_reason == "account_verification":
        messages.success(
            request,
            "You've been accepted and have a slot. Complete phone verification from your dashboard before starting or submitting the task.",
        )
    elif lock_reason == "premium_upgrade":
        messages.success(
            request,
            "You've been accepted and have a slot. Pay the one-time premium upgrade fee from your dashboard before starting or submitting the task.",
        )
    else:
        messages.success(
            request,
            "You've been accepted. You now have a slot in this campaign. "
            "Complete the task and submit your feedback to get paid."
        )
    return redirect("campaigns:reviewer_detail", slug=slug)


@reviewer_required
def reviewer_my_applications(request):
    applications = (
        CampaignApplication.objects
        .filter(reviewer=request.user)
        .select_related("campaign", "campaign__business", "campaign__category")
        .order_by("-applied_at")
    )
    return render(request, "reviewer/my_applications.html", {
        "page_title": "My Applications",
        "nav_active": "applications",
        "applications": applications,
        "surveys_locked": surveys_are_locked(request.user, get_or_create_wallet(request.user)),
        "phone_verification_required": (
            task_access_lock_reason(request.user, get_or_create_wallet(request.user))
            == "account_verification"
        ),
        "platform_settings": get_platform_settings(),
    })