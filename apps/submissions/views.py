from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.campaigns.models import ApplicationStatus, Campaign, CampaignApplication
from apps.common.decorators import business_required, reviewer_required
from apps.common.services import requires_account_verification, surveys_are_locked
from apps.wallets.models import TransactionType
from apps.wallets.services import credit, get_or_create_wallet

from .forms import DynamicQuestionForm
from .models import Submission, SubmissionAnswer, SubmissionStatus


# ---------- Reviewer ----------

@reviewer_required
def start_or_view_submission(request, application_id):
    application = get_object_or_404(
        CampaignApplication.objects.select_related("campaign", "reviewer"),
        pk=application_id,
        reviewer=request.user,
    )

    if application.status not in (ApplicationStatus.ACCEPTED, ApplicationStatus.COMPLETED):
        messages.error(request, "This application is not in a state that allows submission.")
        return redirect("campaigns:reviewer_my_applications")

    submission, created = Submission.objects.get_or_create(
        application=application,
        defaults={
            "campaign": application.campaign,
            "reviewer": request.user,
            "reward_amount": application.campaign.reward_amount,
            "status": SubmissionStatus.DRAFT,
        },
    )

    if submission.status in (SubmissionStatus.VERIFIED, SubmissionStatus.SUBMITTED):
        return redirect("submissions:detail", pk=submission.pk)

    campaign = application.campaign

    if (
        campaign.campaign_type == "SURVEY"
        and surveys_are_locked(request.user, get_or_create_wallet(request.user))
    ):
        messages.error(
            request,
            "This survey is locked. Unlock survey access before submitting it.",
        )
        return redirect("campaigns:reviewer_detail", slug=campaign.slug)

    if request.method == "POST":
        form = DynamicQuestionForm(request.POST, campaign=campaign)
        if form.is_valid():
            with transaction.atomic():
                submission.overall_rating = int(form.cleaned_data["overall_rating"])
                submission.written_feedback = form.cleaned_data["written_feedback"]
                submission.submitted_at = timezone.now()

                auto_verify = getattr(settings, "SUBMISSION_AUTO_VERIFY", False)
                submission.status = (
                    SubmissionStatus.VERIFIED if auto_verify
                    else SubmissionStatus.SUBMITTED
                )
                if auto_verify:
                    submission.verified_at = timezone.now()
                submission.save()

                SubmissionAnswer.objects.filter(submission=submission).delete()
                for q in campaign.questions.all():
                    key = f"q_{q.id}"
                    value = form.cleaned_data.get(key)
                    if value is None or value == "":
                        continue
                    if isinstance(value, list):
                        value = ", ".join(value)
                    SubmissionAnswer.objects.create(
                        submission=submission,
                        question=q,
                        answer_text=str(value),
                    )

                application.status = ApplicationStatus.COMPLETED
                application.completed_at = timezone.now()
                application.save(update_fields=["status", "completed_at"])

                if auto_verify:
                    get_or_create_wallet(request.user)
                    credit(
                        user=request.user,
                        amount=submission.reward_amount,
                        transaction_type=TransactionType.TASK_REWARD,
                        description=f"Reward for: {campaign.title}",
                        reference_type="Submission",
                        reference_id=submission.id,
                        idempotency_key=f"reward-submission-{submission.id}",
                    )
                    if requires_account_verification(
                        request.user,
                        get_or_create_wallet(request.user),
                    ):
                        messages.warning(
                            request,
                            "You reached the account verification threshold. "
                            "Verify your phone number from your profile.",
                        )

            messages.success(
                request,
                f"Submission received. ${submission.reward_amount} has been credited to your wallet."
                if auto_verify else
                "Submission received. It will be reviewed shortly.",
            )
            return redirect("submissions:detail", pk=submission.pk)
    else:
        initial = {}
        if submission.overall_rating:
            initial["overall_rating"] = str(submission.overall_rating)
        if submission.written_feedback:
            initial["written_feedback"] = submission.written_feedback

        for ans in submission.answers.all():
            initial[f"q_{ans.question_id}"] = ans.answer_text

        form = DynamicQuestionForm(campaign=campaign, initial=initial)

    return render(request, "reviewer/submission_form.html", {
        "page_title": "Submit task",
        "nav_active": "applications",
        "campaign": campaign,
        "application": application,
        "submission": submission,
        "form": form,
        "questions_and_fields": list(form.question_fields()),
    })


@reviewer_required
def my_submissions(request):
    submissions = (
        Submission.objects
        .filter(reviewer=request.user)
        .select_related("campaign", "campaign__business")
        .order_by("-created_at")
    )
    return render(request, "reviewer/my_submissions.html", {
        "page_title": "My Submissions",
        "nav_active": "submissions",
        "submissions": submissions,
    })


@reviewer_required
def submission_detail(request, pk):
    submission = get_object_or_404(
        Submission.objects.select_related("campaign", "campaign__business"),
        pk=pk,
        reviewer=request.user,
    )
    answers = submission.answers.select_related("question").order_by("question__order")
    return render(request, "reviewer/submission_detail.html", {
        "page_title": "Submission",
        "nav_active": "submissions",
        "submission": submission,
        "answers": answers,
    })


# ---------- Business (read-only) ----------

@business_required
def business_campaign_submissions(request, pk):
    business = request.user.owned_businesses.first()
    campaign = get_object_or_404(Campaign, pk=pk, business=business)
    submissions = (
        campaign.submissions
        .select_related("reviewer")
        .order_by("-created_at")
    )
    return render(request, "business/campaign_submissions.html", {
        "page_title": f"Submissions · {campaign.title}",
        "nav_active": "campaigns",
        "campaign": campaign,
        "submissions": submissions,
    })