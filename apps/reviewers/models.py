import uuid

from django.conf import settings
from django.db import models

from apps.campaigns.models import Category
from apps.geo.models import Country


class ReviewerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviewer_profile",
    )

    date_of_birth = models.DateField(null=True, blank=True)
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="reviewer_profiles",
        help_text="Country where the reviewer is based.",
    )
    bio = models.TextField(blank=True, max_length=500)

    preferred_categories = models.ManyToManyField(
        Category, blank=True, related_name="interested_reviewers",
    )

    # Trust / activity — updated by services later
    trust_score = models.PositiveSmallIntegerField(default=50)
    total_completed_tasks = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    premium_unlocked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the reviewer paid to unlock surveys.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reviewer profile"
        verbose_name_plural = "Reviewer profiles"

    def __str__(self):
        return f"Profile of {self.user.email}"