from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from apps.accounts.models import UserRole


def role_required(*allowed_roles):
    """
    Decorator for function-based views. Usage:

        @role_required(UserRole.REVIEWER)
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                raise PermissionDenied("You don't have access to this page.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


reviewer_required = role_required(UserRole.REVIEWER)
business_required = role_required(UserRole.BUSINESS)
admin_required = role_required(UserRole.ADMIN)