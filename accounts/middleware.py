# accounts/middleware.py
from django.shortcuts import redirect
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from .onboarding import next_onboarding_step, onboarding_targets, DONE, ROLE_STEP, CATEGORIES_STEP

class OnboardingRedirectMiddleware(MiddlewareMixin):
    """
    If a logged-in user hasn't finished onboarding, force them to the correct step.
    If a user has finished, block direct access to onboarding pages.
    """

    def process_request(self, request):
        user = request.user
        # Allow non-auth users and non-HTML endpoints to pass
        if not user.is_authenticated:
            return None

        step = next_onboarding_step(user)
        targets = onboarding_targets()
        path = request.path

        # Always allow these (static/media/admin/etc.)
        allowed_prefixes = getattr(settings, "ONBOARDING_ALLOWED_PREFIXES", [
            "/static/", "/media/", "/admin/",
        ])

        if any(path.startswith(prefix) for prefix in allowed_prefixes):
            return None

        # If onboarding NOT done → only allow the exact required step path
        if step != DONE:
            required_path = targets[step]
            # allow the required page and POSTs to it; block everything else
            if path != required_path:
                return redirect(required_path)
            return None

        # If onboarding done → block accessing onboarding pages directly
        onboarding_paths = set(targets.values())
        if path in onboarding_paths:
            # send them to your main landing after onboarding (home/explore)
            return redirect("home")  # or "explore"

        return None
