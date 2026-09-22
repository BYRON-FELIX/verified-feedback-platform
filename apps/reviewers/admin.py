from django.contrib import admin

from .models import ReviewerProfile


@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "county", "city", "trust_score",
                    "total_completed_tasks", "total_earnings_ksh")
    search_fields = ("user__email", "city")
    list_filter = ("county", "trust_score")
    filter_horizontal = ("preferred_categories",)