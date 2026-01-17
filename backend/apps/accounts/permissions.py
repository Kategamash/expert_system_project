from functools import wraps
from django.http import HttpResponseForbidden


def role_required(*allowed_roles):
    """
    Usage:
      @role_required(User.Role.OEK, User.Role.LIBRARY_HEAD)
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return HttpResponseForbidden("Требуется вход в систему.")
            if user.role not in allowed_roles and not user.is_superuser:
                return HttpResponseForbidden("Недостаточно прав.")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator