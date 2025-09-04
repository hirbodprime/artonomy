# accounts/onboarding.py
from django.urls import reverse
from .models import User, UserCategory

ROLE_STEP = "role"
CATEGORIES_STEP = "categories"
DONE = "done"

def next_onboarding_step(user: User) -> str:
    if not user.is_authenticated:
        return DONE  # not our concern here

    # Step 1: no role yet → choose_role
    if not user.role:
        return ROLE_STEP

    # Step 2: role set → require at least one category for that role-kind
    rel_kind = (
        UserCategory.Kind.WORK
        if user.role == User.Role.ARTIST
        else UserCategory.Kind.FAV
    )
    has_any_for_kind = UserCategory.objects.filter(
        user=user, kind=rel_kind
    ).exists()
    if not has_any_for_kind:
        return CATEGORIES_STEP

    # Finished
    return DONE


def onboarding_targets():
    """Centralize paths used by the middleware (avoids reverse calls all over)."""
    return {
        ROLE_STEP: reverse("choose_role"),
        CATEGORIES_STEP: reverse("choose_categories"),
    }
