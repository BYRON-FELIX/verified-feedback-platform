from django.urls import path

from . import views

app_name = "campaigns"

urlpatterns = [
    # Business
    path("business/", views.business_campaign_list, name="business_list"),
    path("business/new/", views.business_campaign_create, name="business_create"),
    path("business/<uuid:pk>/", views.business_campaign_detail, name="business_detail"),
    path("business/application/<uuid:pk>/reject/", views.business_application_reject, name="business_application_reject"),

    # Reviewer
    path("reviewer/", views.reviewer_campaign_list, name="reviewer_list"),
    path("reviewer/my-applications/", views.reviewer_my_applications, name="reviewer_my_applications"),
    path("reviewer/<slug:slug>/", views.reviewer_campaign_detail, name="reviewer_detail"),
    path("reviewer/<slug:slug>/apply/", views.reviewer_campaign_apply, name="reviewer_apply"),
]