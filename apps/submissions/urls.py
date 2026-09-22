from django.urls import path

from . import views

app_name = "submissions"

urlpatterns = [
    path("start/<uuid:application_id>/", views.start_or_view_submission, name="start"),
    path("mine/", views.my_submissions, name="mine"),
    path("<uuid:pk>/", views.submission_detail, name="detail"),
    path("business/campaign/<uuid:pk>/", views.business_campaign_submissions, name="business_campaign_submissions"),
]