# core/middleware/guest_readonly.py
from urllib.parse import urlencode
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from django.utils.translation import get_language
from django.urls import translate_url

class GuestReadOnlyMiddleware:
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, get_response):
        self.get_response = get_response
        # Compute once at startup; fallback to hard path if name not found
        try:
            self.LANG_SWITCH_PATH = reverse("set_language")   # or "set_language_auth" if that's your name
        except Exception:
            self.LANG_SWITCH_PATH = "/i18n/setlang/"

        # Exact paths guests may access freely
        self.EXEMPT_EXACT = {
            # public entry points
            reverse("landing"),
            reverse("signup"),
            self.LANG_SWITCH_PATH,         # ✅ allow language switcher (POST OK)
        }

        # Prefixes always allowed
        self.EXEMPT_PREFIXES = (
            getattr(settings, "STATIC_URL", "/static/") or "/static/",
            getattr(settings, "MEDIA_URL", "/media/") or "/media/",
            "/admin",
            "/i18n/",                      # ✅ allow any i18n assets/routes if needed
        )

        self.DENY_PREFIXES = (
            "/network/toggle-follow/",
            "/posts/like/",
            "/posts/save/",
            "/posts/comment/",
            "/posts/new/",
            "/suggest/toggle/",
            "/market/add/",
            "/collab/",
            "/account/settings/",
            "/account/logout/",
            "/dashboard/",
            "/portfolio/themes/",
            "/portfolio/onboarding/",
            "/portfolio/me/",
        )

        self.DENY_CONTAINS = (
            "/toggle",
            "/fav/",
            "/review/",
            "/media/",
            "/category/",
            "/portfolio/@",
        )

    def _redirect_to_landing(self, request):
        try:
            landing_url = reverse("landing")
        except Exception:
            landing_url = "/landing/"
        # Keep current language in the redirect
        landing_url = translate_url(landing_url, get_language())
        params = urlencode({"next": request.get_full_path()})
        return redirect(f"{landing_url}?{params}")

    def __call__(self, request):
        user = getattr(request, "user", None)
        path = request.path

        # Always allow static/media/admin/i18n and exact exempt paths (incl. setlang)
        if any(path.startswith(pfx) for pfx in self.EXEMPT_PREFIXES) or path in self.EXEMPT_EXACT:
            return self.get_response(request)

        # Authenticated users: allow through
        if user and user.is_authenticated:
            return self.get_response(request)

        # ----- Guests below -----

        # Block non-safe methods (POST/PUT/DELETE) ...
        # ... except our language switch endpoint which we already allowed above.
        if request.method not in self.SAFE_METHODS:
            return self._redirect_to_landing(request)

        # Block private/action GET endpoints
        if any(path.startswith(pfx) for pfx in self.DENY_PREFIXES):
            return self._redirect_to_landing(request)
        if any(substr in path for substr in self.DENY_CONTAINS):
            return self._redirect_to_landing(request)

        return self.get_response(request)
