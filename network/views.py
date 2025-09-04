from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Exists, OuterRef, Max
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from urllib.parse import urlencode
from accounts.models import UserCategory  # add
from .models import Follow

User = get_user_model()


def _annotate_i_follow(qs, request):
    if request.user.is_authenticated:
        return qs.annotate(
            i_follow=Exists(
                Follow.objects.filter(follower=request.user, following=OuterRef("pk"))
            )
        )
    return qs.annotate(i_follow=Exists(Follow.objects.none()))


def _paginate(request, qs, per_page=24):
    paginator = Paginator(qs, per_page)
    return paginator.get_page(request.GET.get("page") or 1)


def followers_list(request, username: str):
    profile_user = get_object_or_404(User.objects.select_related("profile"), username=username)
    q = (request.GET.get("q") or "").strip()

    base = (
        User.objects
        .filter(following_relations__following=profile_user)
        .select_related("profile")
        .prefetch_related("usercategory_set__category")  # ← so we can show artist work categories
        .distinct()
        .annotate(last_follow=Max(
            "following_relations__created_at",
            filter=Q(following_relations__following=profile_user)
        ))
        .order_by("-last_follow", "username")
    )
    if q:
        base = base.filter(Q(username__icontains=q) | Q(profile__title__icontains=q))

    users = _annotate_i_follow(base, request)
    page_obj = _paginate(request, users)

    return render(request, "network/follow_list.html", {
        "nav_active": None,
        "active_tab": "followers",
        "profile_user": profile_user,
        "followers_count": profile_user.follower_relations.count(),
        "following_count": profile_user.following_relations.count(),
        "q": q,
        "page_obj": page_obj,
        "UC_KIND_WORK": UserCategory.Kind.WORK,      # pass Kind for template checks
        "ROLE_ARTIST": User.Role.ARTIST,
        "ROLE_AUDIENCE": User.Role.AUDIENCE,
    })


def following_list(request, username: str):
    profile_user = get_object_or_404(User.objects.select_related("profile"), username=username)
    q = (request.GET.get("q") or "").strip()

    base = (
        User.objects
        .filter(follower_relations__follower=profile_user)
        .select_related("profile")
        .prefetch_related("usercategory_set__category")  # ← same here
        .distinct()
        .annotate(last_follow=Max(
            "follower_relations__created_at",
            filter=Q(follower_relations__follower=profile_user)
        ))
        .order_by("-last_follow", "username")
    )
    if q:
        base = base.filter(Q(username__icontains=q) | Q(profile__title__icontains=q))

    users = _annotate_i_follow(base, request)
    page_obj = _paginate(request, users)

    return render(request, "network/follow_list.html", {
        "nav_active": None,
        "active_tab": "following",
        "profile_user": profile_user,
        "followers_count": profile_user.follower_relations.count(),
        "following_count": profile_user.following_relations.count(),
        "q": q,
        "page_obj": page_obj,
        "UC_KIND_WORK": UserCategory.Kind.WORK,
        "ROLE_ARTIST": User.Role.ARTIST,
        "ROLE_AUDIENCE": User.Role.AUDIENCE,
    })


@login_required
def toggle_follow(request, user_id: int):
    """Follow/unfollow and redirect back (supports AJAX too)."""
    target = get_object_or_404(User, pk=user_id)
    next_url = request.GET.get("next") or request.POST.get("next")

    if target == request.user:
        messages.error(request, "You can’t follow yourself.")
        return redirect(next_url or "profile_view", username=target.username)

    obj, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        obj.delete()
        status = "unfollowed"
    else:
        status = "followed"

    # AJAX support
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": status})

    return redirect(next_url or "profile_view", username=target.username)
