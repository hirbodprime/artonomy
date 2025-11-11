# artists/views.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count   # ⬅️ add this
from .models import Category, Subcategory
from accounts.models import Profile


def category_grid(request):
    cats = Category.objects.all().prefetch_related("subcategories")
    return render(request, "artists/category_grid.html", {"items": cats})


def subcategory_grid(request, cat_slug):
    category = get_object_or_404(Category, slug=cat_slug)
    items = (
        Subcategory.objects
        .filter(category=category)
        .annotate(
            artist_count=Count(
                "profiles",
                filter=Q(profiles__role="artist", profiles__completion=100),
            )
        )
        .order_by("order", "name")
    )
    return render(
        request,
        "artists/subcategory_grid.html",
        {"category": category, "items": items},
    )


def subcat_artists_grid(request, cat_slug, sub_slug):
    category = get_object_or_404(Category, slug=cat_slug)
    subcategory = get_object_or_404(Subcategory, slug=sub_slug, category=category)

    items = (
        Profile.objects.filter(
            role="artist",
            category=category,
            subcategory=subcategory,
            completion=100,           # ⬅️ فقط پروفایل ۱۰۰٪
        )
        .select_related("user")
    )

    return render(
        request,
        "artists/subcat_artists_grid.html",
        {
            "category": category,
            "subcategory": subcategory,
            "items": items,
        },
    )
