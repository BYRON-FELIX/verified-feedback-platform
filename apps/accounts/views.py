from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import BusinessSignupForm, ReviewerSignupForm


def reviewer_signup(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        form = ReviewerSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Ensure profile exists
            from apps.reviewers.models import ReviewerProfile
            ReviewerProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, "Welcome! Your reviewer account is ready.")
            return redirect("/dashboard/")
    else:
        form = ReviewerSignupForm()
    return render(request, "auth/signup_reviewer.html", {"form": form})


def business_signup(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        form = BusinessSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your business account is ready.")
            return redirect("/")
    else:
        form = BusinessSignupForm()
    return render(request, "auth/signup_business.html", {"form": form})