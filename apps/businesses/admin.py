from django.contrib import admin

from .models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "verified_badge", "created_at")
    list_filter = ("status", "verified_badge")
    search_fields = ("name", "owner__email")
    prepopulated_fields = {"slug": ("name",)}