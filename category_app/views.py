# views.py
from django.db.models import Count, Q, Value, F
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404

from accounts.models import Category, User, UserCategory


def category_index(request):
    categories = (
        Category.objects
        .annotate(
            artist_count=Count(
                "usercategory",
                filter=Q(usercategory__kind=UserCategory.Kind.WORK,
                         usercategory__user__role=User.Role.ARTIST),
                distinct=True,
            )
        )
        .order_by("name")
    )

    has_work = False
    if request.user.is_authenticated:
        has_work = UserCategory.objects.filter(
            user=request.user,
            kind=UserCategory.Kind.WORK
        ).exists()

    return render(
        request,
        "category/index.html",
        {
            "categories": categories,
            "nav_active": "category",
            "has_work": has_work,  # ✅
        },
    )


# views.py  (category_artists)
def category_artists(request, slug):
    category = get_object_or_404(Category, slug=slug)
    sort = (request.GET.get("sort") or "latest").lower()

    artists = (
        User.objects.filter(
            role=User.Role.ARTIST,
            usercategory__category=category,
            usercategory__kind=UserCategory.Kind.WORK,
        )
        .prefetch_related("categories")
        .annotate(
            followers_count=Coalesce(Count("follower_relations", distinct=True), Value(0)),
            following_count=Coalesce(Count("following_relations", distinct=True), Value(0)),
        )
        .distinct()
    )

    if sort == "followers":
        artists = artists.order_by("-followers_count", "username")
    else:  # latest
        sort = "latest"
        artists = artists.order_by("-date_joined")

    paginator = Paginator(artists, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    following_ids = set()
    if request.user.is_authenticated:
        following_ids = set(
            request.user.following_relations.values_list("following_id", flat=True)
        )

    return render(request, "category/detail.html", {
        "nav_active": "category",

        "category": category,
        "artists": page_obj,
        "page_obj": page_obj,
        "sort": sort,
        "current_query": request.GET.urlencode(),
        "following_ids": following_ids,
    })
