from django.contrib import admin

from .models import ReviewerProfile


@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "country", "county", "city", "trust_score",
                    "total_completed_tasks", "total_earnings", "premium_unlocked_at")
    search_fields = ("user__email", "city")
    list_filter = ("country", "county", "trust_score")
    filter_horizontal = ("preferred_categories",)