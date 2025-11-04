# accounts/onboarding.py
from django.urls import reverse
from .models import User, UserCategory
from django.conf import settings

ROLE_STEP = "role"
CATEGORIES_STEP = "categories"
DONE = "done"


def next_onboarding_step(user: User) -> str:
    # short-circuit if disabled
    if not getattr(settings, "ONBOARDING_ENABLED", True):
        return DONE

    if not user.is_authenticated:
        return DONE

    if not user.role:
        return ROLE_STEP

    rel_kind = UserCategory.Kind.WORK if user.role == User.Role.ARTIST else UserCategory.Kind.FAV
    if not UserCategory.objects.filter(user=user, kind=rel_kind).exists():
        return CATEGORIES_STEP

    return DONE


def onboarding_targets():
    """Centralize paths used by the middleware (avoids reverse calls all over)."""
    return {
        ROLE_STEP: reverse("choose_role"),
        CATEGORIES_STEP: reverse("choose_categories"),
    }
