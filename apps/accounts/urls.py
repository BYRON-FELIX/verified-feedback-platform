from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import EmailAuthenticationForm

app_name = "accounts"

urlpatterns = [
    path("referrals/", views.referrals, name="referrals"),
    path("signup/reviewer/", views.reviewer_signup, name="signup_reviewer"),
    path("signup/business/", views.business_signup, name="signup_business"),
    path("login/", auth_views.LoginView.as_view(
        template_name="auth/login.html",
        authentication_form=EmailAuthenticationForm,
        redirect_authenticated_user=True,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
]