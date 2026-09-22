import uuid

from django.conf import settings
from django.db import models

from apps.campaigns.models import Campaign, CampaignApplication


class SubmissionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"
    FLAGGED = "FLAGGED", "Flagged"


class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        CampaignApplication,
        on_delete=models.PROTECT,
        related_name="submission",
    )
    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name="submissions")
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submissions",
    )

    status = models.CharField(
        max_length=16, choices=SubmissionStatus.choices, default=SubmissionStatus.DRAFT
    )

    overall_rating = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="1–5 stars. Reviewer decides freely.",
    )
    written_feedback = models.TextField(
        blank=True,
        help_text="Reviewer's written account of their experience.",
    )

    experience_date = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    reward_amount_ksh = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Snapshot of the reward at submission time.",
    )

    rejection_reason = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(overall_rating__isnull=True) | models.Q(overall_rating__gte=1, overall_rating__lte=5),
                name="submission_rating_range",
            ),
        ]

    def __str__(self):
        return f"{self.reviewer.email} → {self.campaign.title} ({self.status})"


class SubmissionAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(
        "campaigns.CampaignQuestion",
        on_delete=models.PROTECT,
        related_name="answers",
    )
    answer_text = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "question"],
                name="uniq_answer_per_submission_question",
            )
        ]

    def __str__(self):
        return f"Q: {self.question.text[:40]} → {self.answer_text[:40]}"