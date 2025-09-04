# core/middleware/require_login.py
from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class RequireLoginMiddleware:
    """
    Middleware that redirects any unauthenticated user to the landing page,
    unless they're accessing allowed URLs.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            reverse("landing"),    # your landing page
            # reverse("login"),      # login page
            reverse("signup"),     # signup page
        ]

    def __call__(self, request):
        # allow admin, static, media, and exempt urls
        if (
            not request.user.is_authenticated
            and not request.path.startswith("/admin")
            and not request.path.startswith(settings.STATIC_URL)
            and not request.path.startswith(settings.MEDIA_URL)
            and request.path not in self.exempt_urls
        ):
            return redirect("landing")

        return self.get_response(request)
