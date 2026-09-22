from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
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

@login_required
@require_http_methods(["GET", "POST"])
def seed_demo_data(request):
    """
    Superuser-only endpoint to seed demo data on a deployed environment
    (where shell access is not available, e.g. Render free tier).

    Usage: visit /seed-demo-data/ while logged in as superuser.
    Optional query params:
        ?count=100
        ?clear=1
    """
    if not (request.user.is_superuser or request.user.role == "ADMIN"):
        return HttpResponseForbidden("Superuser only.")

    from io import StringIO

    out = StringIO()
    count = int(request.GET.get("count", 100))
    clear = request.GET.get("clear") in ("1", "true", "yes")

    args = ["--count", str(count), "--force"]
    if clear:
        args.append("--clear")

    call_command("seed_campaigns", *args, stdout=out)

    return HttpResponse(
        "<pre>" + out.getvalue() + "</pre>",
        content_type="text/html",
    )