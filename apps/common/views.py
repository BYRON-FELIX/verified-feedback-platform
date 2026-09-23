from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import UserRole


def landing(request):
    if request.user.is_authenticated:
        return redirect("/dashboard/")
    return render(request, "landing/index.html")


@login_required
def dashboard_router(request):
    """Send the user to the correct dashboard based on role."""
    if request.user.is_superuser or request.user.role == UserRole.ADMIN:
        return redirect("/django-admin/")
    if request.user.role == UserRole.BUSINESS:
        return redirect("/business/")
    return redirect("/reviewer/")

