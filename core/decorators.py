from functools import wraps
from django.shortcuts import redirect

def redirect_if_authenticated(to="landing"):
    """
    If user is already logged in, redirect to `to`.
    Use on views meant only for anonymous users (signup/login/password reset start).
    """
    def _dec(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_authenticated:
                return redirect(to)
            return view_func(request, *args, **kwargs)
        return _wrapped
    return _dec
