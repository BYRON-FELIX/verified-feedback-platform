from django.contrib import admin

from .models import ReviewerProfile


@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "country", "trust_score",
                    "total_completed_tasks", "total_earnings", "premium_unlocked_at")
    search_fields = ("user__email",)
    list_filter = ("country", "trust_score")
    filter_horizontal = ("preferred_categories",)