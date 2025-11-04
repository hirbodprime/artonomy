# core/middleware/guest_readonly.py
from urllib.parse import urlencode
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.utils.translation import get_language
from django.urls import translate_url


class GuestReadOnlyMiddleware:
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, get_response):
        self.get_response = get_response

        # Resolve helpers (tolerant to missing routes in some envs)
        def _rv(name, default):
            try:
                return reverse(name)
            except NoReverseMatch:
                return default

        # Common named routes (best effort)
        self.LANG_SWITCH_PATH = _rv("set_language", "/i18n/setlang/")
        self.LANDING_PATH      = _rv("landing", "/landing/")
        self.SIGNUP_PATH       = _rv("signup", "/signup/")
        self.HOME_PATH         = _rv("home", "/")
        self.EXPLORE_PATH      = _rv("explore", "/explore/")
        self.CATEGORIES_INDEX  = _rv("categories:index", "/categories/")
        self.MK_HOME_PATH      = _rv("marketplace:home", "/marketplace/")
        # Optional public detail pages (ok if missing)
        self.MK_PROFILE_PATH   = _rv("marketplace:profile", "/marketplace/p/")  # prefix allow
        self.MK_PRODUCT_PATH   = _rv("marketplace:product_detail", "/marketplace/item/")  # prefix allow

        # Exact paths guests may access freely
        self.EXEMPT_EXACT = {
            self.LANDING_PATH,
            self.SIGNUP_PATH,
            self.LANG_SWITCH_PATH,
            self.HOME_PATH,
            self.EXPLORE_PATH,
            self.CATEGORIES_INDEX,
            self.MK_HOME_PATH,
        }

        # Prefixes always allowed (public pages + static/media/admin/i18n)
        self.EXEMPT_PREFIXES = tuple(filter(None, (
            getattr(settings, "STATIC_URL", "/static/") or "/static/",
            getattr(settings, "MEDIA_URL", "/media/") or "/media/",
            "/admin",
            "/i18n/",
            # public detail prefixes
            self.MK_PROFILE_PATH.rsplit("/", 1)[0] if self.MK_PROFILE_PATH else None,
            self.MK_PRODUCT_PATH.rsplit("/", 1)[0] if self.MK_PRODUCT_PATH else None,
        )))

        # Private/action endpoints that should ALWAYS require auth
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

        # Keep DENY_CONTAINS tight (previously caught legit pages like /category/)
        self.DENY_CONTAINS = (
            "/toggle",
            "/fav/",
            "/review/",
        )

    def _translated(self, path: str) -> str:
        # Make sure allowlist comparisons use the same locale style as request
        return translate_url(path, get_language())

    def _redirect_to_landing(self, request):
        landing_url = self._translated(self.LANDING_PATH)
        # Loop guard: if we’re already on landing, don't add ?next to landing again
        if request.path.startswith(landing_url.rstrip("/")):
            return self.get_response(request)
        params = urlencode({"next": request.get_full_path()})
        return redirect(f"{landing_url}?{params}")

    def __call__(self, request):
        user = getattr(request, "user", None)
        path = request.path

        # Normalize translated versions of exempt exact paths
        translated_exacts = {self._translated(p) for p in self.EXEMPT_EXACT}

        # Always allow static/media/admin/i18n and exact exempt paths
        if any(path.startswith(pfx) for pfx in self.EXEMPT_PREFIXES) or path in translated_exacts:
            return self.get_response(request)

        # Authenticated users: allow through
        if user and user.is_authenticated:
            return self.get_response(request)

        # ----- Guests below -----

        # Don’t block safe public GETs unless they’re clearly actions
        if request.method not in self.SAFE_METHODS:
            return self._redirect_to_landing(request)

        # Block private/action GET endpoints
        if any(path.startswith(pfx) for pfx in self.DENY_PREFIXES):
            return self._redirect_to_landing(request)
        if any(substr in path for substr in self.DENY_CONTAINS):
            return self._redirect_to_landing(request)

        # Otherwise let guests view the page
        return self.get_response(request)
