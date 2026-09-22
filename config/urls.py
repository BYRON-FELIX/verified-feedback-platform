from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.views import dashboard_router, landing

urlpatterns = [
    path("", landing, name="landing"),
    path("dashboard/", dashboard_router, name="dashboard"),
    path("auth/", include("apps.accounts.urls")),
    path("reviewer/", include("apps.reviewers.urls")),
    path("business/", include("apps.businesses.urls")),
    path("campaigns/", include("apps.campaigns.urls")),
    path("submissions/", include("apps.submissions.urls")),   # ← this line
    path("withdrawals/", include("apps.withdrawals.urls")),
   
    path("django-admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)