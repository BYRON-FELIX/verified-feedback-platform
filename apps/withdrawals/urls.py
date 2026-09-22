from django.urls import path

from . import views

app_name = "withdrawals"

urlpatterns = [
    # Reviewer
    path("wallet/", views.wallet_view, name="wallet"),
    path("request/", views.request_withdrawal_view, name="request"),
    path("mine/", views.withdrawal_list, name="list"),
    path("<uuid:pk>/", views.withdrawal_detail, name="detail"),

    # Admin
    path("admin/queue/", views.admin_withdrawal_queue, name="admin_queue"),
    path("admin/<uuid:pk>/<str:action>/", views.admin_withdrawal_action, name="admin_action"),
]