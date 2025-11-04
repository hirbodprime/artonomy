# accounts/middleware.py
from django.conf import settings
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from .onboarding import next_onboarding_step, onboarding_targets, DONE

class OnboardingRedirectMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # if disabled, do nothing
        if not getattr(settings, "ONBOARDING_ENABLED", True):
            return None

        user = request.user
        if not user.is_authenticated:
            return None

        step = next_onboarding_step(user)
        targets = onboarding_targets()
        path = request.path

        allowed_prefixes = getattr(settings, "ONBOARDING_ALLOWED_PREFIXES", ["/static/", "/media/", "/admin/"])
        if any(path.startswith(prefix) for prefix in allowed_prefixes):
            return None

        if step != DONE:
            required_path = targets[step]
            if path != required_path:
                return redirect(required_path)
            return None

        if path in set(targets.values()):
            return redirect("marketplace:home")  # or "explore"

        return None
