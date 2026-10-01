from django.contrib import admin

from .models import Submission, SubmissionAnswer


class SubmissionAnswerInline(admin.TabularInline):
    model = SubmissionAnswer
    extra = 0
    readonly_fields = ("question", "answer_text")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("campaign", "reviewer", "status", "overall_rating",
                    "reward_amount", "submitted_at", "verified_at")
    list_filter = ("status",)
    search_fields = ("campaign__title", "reviewer__email")
    inlines = [SubmissionAnswerInline]
    readonly_fields = ("created_at", "updated_at", "submitted_at", "verified_at")

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser