from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("survey-unlock/", views.start_survey_unlock, name="survey_unlock"),
    path("stkpush-test/", views.stkpush_test, name="stkpush_test"),
    path("payhero/callback/", views.payhero_callback, name="payhero_callback"),
]
