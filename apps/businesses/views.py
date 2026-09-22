from django.contrib import messages
from django.shortcuts import redirect, render

from apps.common.decorators import business_required

from .forms import BusinessProfileForm
from .models import Business


@business_required
def dashboard(request):
    business = request.user.owned_businesses.first()
    context = {
        "page_title": "Business Dashboard",
        "nav_active": "dashboard",
        "business": business,
    }
    return render(request, "business/dashboard.html", context)


@business_required
def profile(request):
    business = request.user.owned_businesses.first()

    if request.method == "POST":
        form = BusinessProfileForm(request.POST, request.FILES, instance=business)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            messages.success(request, "Business profile saved.")
            return redirect("businesses:profile")
    else:
        form = BusinessProfileForm(instance=business)

    return render(request, "business/profile.html", {
        "page_title": "Business Profile",
        "nav_active": "profile",
        "form": form,
        "business": business,
    })