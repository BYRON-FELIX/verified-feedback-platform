from django.urls import path

from . import views

app_name = "reviewers"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("profile/password/", views.change_password, name="change_password"),
]