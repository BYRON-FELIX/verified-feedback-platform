from django.contrib import admin

from .models import (
    Campaign,
    CampaignApplication,
    CampaignQuestion,
    CampaignRequirement,
    Category,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}


class RequirementInline(admin.TabularInline):
    model = CampaignRequirement
    extra = 1


class QuestionInline(admin.TabularInline):
    model = CampaignQuestion
    extra = 1


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "title", "business", "campaign_type", "status",
        "reward_amount_ksh", "target_participants", "filled_slots",
        "start_date", "end_date",
    )
    list_filter = ("status", "campaign_type", "category")
    search_fields = ("title", "business__name")
    inlines = [RequirementInline, QuestionInline]
    readonly_fields = ("filled_slots", "created_at", "updated_at")


@admin.register(CampaignApplication)
class CampaignApplicationAdmin(admin.ModelAdmin):
    list_display = ("campaign", "reviewer", "status", "applied_at", "accepted_at")
    list_filter = ("status",)
    search_fields = ("campaign__title", "reviewer__email")
    readonly_fields = ("applied_at", "accepted_at", "rejected_at", "completed_at")