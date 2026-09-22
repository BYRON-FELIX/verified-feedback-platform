from django.contrib import admin

from .models import Country, County


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "currency_code", "phone_prefix", "is_active")
    search_fields = ("name", "code")


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "is_active")
    list_filter = ("country", "is_active")
    search_fields = ("name",)