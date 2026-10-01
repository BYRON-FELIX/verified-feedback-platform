import uuid

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.businesses.models import Business
from apps.geo.models import County


class CampaignType(models.TextChoices):
    REVIEW = "REVIEW", "Review"
    SURVEY = "SURVEY", "Survey"
    MYSTERY_SHOPPING = "MYSTERY_SHOPPING", "Mystery Shopping"
    PRODUCT_TESTING = "PRODUCT_TESTING", "Product Testing"
    SERVICE_TESTING = "SERVICE_TESTING", "Service Testing"


class CampaignStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending approval"
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    REJECTED = "REJECTED", "Rejected"


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    icon = models.CharField(max_length=40, blank=True, help_text="Bootstrap icon class, e.g. bi-cup-hot")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Campaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="campaigns")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns",
    )

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(help_text="What this campaign is about.")
    instructions = models.TextField(
        blank=True,
        help_text="Step-by-step instructions for the reviewer.",
    )

    campaign_type = models.CharField(
        max_length=32, choices=CampaignType.choices, default=CampaignType.SURVEY
    )
    status = models.CharField(
        max_length=24, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT
    )

    # Amounts in USD
    reward_amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    target_participants = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    filled_slots = models.PositiveIntegerField(default=0)

    budget_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    start_date = models.DateField()
    end_date = models.DateField()

    county = models.ForeignKey(
        County, on_delete=models.SET_NULL, null=True, blank=True, related_name="campaigns"
    )
    location_description = models.CharField(max_length=160, blank=True)

    estimated_minutes = models.PositiveIntegerField(
        default=10, help_text="Estimated time to complete, in minutes."
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    is_seed_data = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "end_date"]),
            models.Index(fields=["category", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(filled_slots__lte=models.F("target_participants")),
                name="campaign_filled_not_exceed_target",
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="campaign_end_after_start",
            ),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:160] or "campaign"
            candidate = base
            n = 1
            while Campaign.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def slots_remaining(self):
        return max(self.target_participants - self.filled_slots, 0)

    @property
    def is_open(self):
        return self.status == CampaignStatus.ACTIVE and self.slots_remaining > 0


class CampaignRequirement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="requirements")
    text = models.CharField(max_length=300)
    is_mandatory = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "text"]

    def __str__(self):
        return self.text


class CampaignQuestionType(models.TextChoices):
    TEXT = "TEXT", "Short text"
    LONG_TEXT = "LONG_TEXT", "Long text"
    SINGLE_CHOICE = "SINGLE_CHOICE", "Single choice"
    MULTI_CHOICE = "MULTI_CHOICE", "Multiple choice"
    RATING = "RATING", "Rating (1-5)"
    YES_NO = "YES_NO", "Yes / No"
    NUMBER = "NUMBER", "Number"


class CampaignQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=400)
    question_type = models.CharField(
        max_length=24, choices=CampaignQuestionType.choices, default=CampaignQuestionType.TEXT
    )
    options = models.JSONField(
        default=list, blank=True,
        help_text="For choice types: list of option strings.",
    )
    is_required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "text"]

    def __str__(self):
        return self.text

class ApplicationStatus(models.TextChoices):
    APPLIED = "APPLIED", "Applied"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    COMPLETED = "COMPLETED", "Completed"


class CampaignApplication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="applications")
    reviewer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="campaign_applications",
    )
    status = models.CharField(
        max_length=16,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.APPLIED,
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    withdraw_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "reviewer"],
                name="uniq_application_per_campaign_reviewer",
            )
        ]
        indexes = [
            models.Index(fields=["reviewer", "status"]),
            models.Index(fields=["campaign", "status"]),
        ]

    def __str__(self):
        return f"{self.reviewer.email} → {self.campaign.title} ({self.status})"