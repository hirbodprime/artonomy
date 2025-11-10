# core/views_admin.py
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Profile
from artists.models import Category, Subcategory
from marketplace.models import Product, Service, ArtPost
from core.models import Visit

User = get_user_model()


@staff_member_required  # ✅ only staff / admin can see this
def admin_kpi_dashboard(request):
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # ───── Users & Profiles ─────
    total_users = User.objects.count()
    total_profiles = Profile.objects.count()
    completed_profiles = Profile.objects.filter(completion=100).count()
    avg_completion = Profile.objects.aggregate(avg=Avg("completion"))["avg"] or 0

    # new users / profiles
    users_last_7 = (
        User.objects.filter(date_joined__gte=week_ago).count()
        if hasattr(User, "date_joined")
        else None
    )
    profiles_last_7 = Profile.objects.filter(created_at__gte=week_ago).count()

    # Role distribution
    role_breakdown = (
        Profile.objects
        .values("role")
        .annotate(c=Count("id"))
        .order_by("-c")
    )

    # Category usage
    top_categories = (
        Category.objects
        .annotate(profile_count=Count("profiles"))
        .order_by("-profile_count", "order", "name")[:10]
    )

    top_subcategories = (
        Subcategory.objects
        .annotate(profile_count=Count("profiles"))
        .order_by("-profile_count", "category__order", "order", "name")[:10]
    )

    # ───── Marketplace KPIs ─────
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    products_last_7 = Product.objects.filter(created_at__gte=week_ago).count()
    products_last_30 = Product.objects.filter(created_at__gte=month_ago).count()

    total_services = Service.objects.count()
    active_services = Service.objects.filter(is_active=True).count()
    services_last_7 = Service.objects.filter(created_at__gte=week_ago).count()
    services_last_30 = Service.objects.filter(created_at__gte=month_ago).count()

    total_artposts = ArtPost.objects.count()
    active_artposts = ArtPost.objects.filter(is_active=True).count()
    artposts_last_7 = ArtPost.objects.filter(created_at__gte=week_ago).count()
    artposts_last_30 = ArtPost.objects.filter(created_at__gte=month_ago).count()
    artposts_with_likes = ArtPost.objects.filter(likes__isnull=False).distinct().count()
    # ───── Visit KPIs ─────
    # ───── Visit KPIs ─────
    total_visits = Visit.objects.count()
    visits_last_7 = Visit.objects.filter(created_at__gte=week_ago).count()
    visits_last_30 = Visit.objects.filter(created_at__gte=month_ago).count()

    # Unique visitors
    unique_visitors_all = Visit.objects.values("visitor_id").distinct().count()
    unique_visitors_30 = (
        Visit.objects
        .filter(created_at__gte=month_ago)
        .values("visitor_id")
        .distinct()
        .count()
    )

    # All QR scans (lifetime + 30 days)
    qr_visits_total = Visit.objects.filter(utm_source="qr").count()
    qr_visits_30 = Visit.objects.filter(
        utm_source="qr",
        created_at__gte=month_ago,
    ).count()

    # Breakdown per campaign – lifetime
    artists_poster_total = Visit.objects.filter(
        utm_source="qr",
        utm_campaign="artists",
    ).count()
    audience_poster_total = Visit.objects.filter(
        utm_source="qr",
        utm_campaign="audience",
    ).count()
    visitcard_total = Visit.objects.filter(
        utm_source="qr",
        utm_campaign="visitcard",
    ).count()

    # Breakdown per campaign – last 30 days
    artists_poster_30 = Visit.objects.filter(
        utm_source="qr",
        utm_campaign="artists",
        created_at__gte=month_ago,
    ).count()
    audience_poster_30 = Visit.objects.filter(
        utm_source="qr",
        utm_campaign="audience",
        created_at__gte=month_ago,
    ).count()
    visitcard_30 = Visit.objects.filter(
        utm_source="qr",
        utm_campaign="visitcard",
        created_at__gte=month_ago,
    ).count()

    # direct = بدون utm_source و بدون referrer
    direct_visits_total = Visit.objects.filter(
        utm_source="",
        referrer="",
    ).count()
    direct_visits_30 = Visit.objects.filter(
        created_at__gte=month_ago,
        utm_source="",
        referrer="",
    ).count()

    # Top creators by products/services/artposts
    top_profiles_by_products = (
        Profile.objects
        .annotate(products_count=Count("products"))
        .filter(products_count__gt=0)
        .order_by("-products_count")[:10]
    )

    top_profiles_by_services = (
        Profile.objects
        .annotate(services_count=Count("services"))
        .filter(services_count__gt=0)
        .order_by("-services_count")[:10]
    )

    top_profiles_by_artposts = (
        Profile.objects
        .annotate(artposts_count=Count("artposts"))
        .filter(artposts_count__gt=0)
        .order_by("-artposts_count")[:10]
    )

    # ───── Latest items for quick access ─────
    latest_products = (
        Product.objects
        .select_related("profile", "profile__user")
        .order_by("-created_at")[:10]
    )

    latest_services = (
        Service.objects
        .select_related("profile", "profile__user")
        .order_by("-created_at")[:10]
    )

    latest_artposts = (
        ArtPost.objects
        .select_related("profile", "profile__user")
        .order_by("-created_at")[:10]
    )

    context = {
        "now": now,

        # Users & Profiles
        "total_users": total_users,
        "total_profiles": total_profiles,
        "completed_profiles": completed_profiles,
        "avg_completion": round(avg_completion, 1),
        "users_last_7": users_last_7,
        "profiles_last_7": profiles_last_7,
        "role_breakdown": role_breakdown,
        "top_categories": top_categories,
        "top_subcategories": top_subcategories,

        # Marketplace
        "total_products": total_products,
        "active_products": active_products,
        "products_last_7": products_last_7,
        "products_last_30": products_last_30,
        "total_services": total_services,
        "active_services": active_services,
        "services_last_7": services_last_7,
        "services_last_30": services_last_30,
        "total_artposts": total_artposts,
        "active_artposts": active_artposts,
        "artposts_last_7": artposts_last_7,
        "artposts_last_30": artposts_last_30,
        "artposts_with_likes": artposts_with_likes,

        # Top profiles
        "top_profiles_by_products": top_profiles_by_products,
        "top_profiles_by_services": top_profiles_by_services,
        "top_profiles_by_artposts": top_profiles_by_artposts,

        # Latest items
        "latest_products": latest_products,
        "latest_services": latest_services,
        "latest_artposts": latest_artposts,


        # Visits (overall)
        "total_visits": total_visits,
        "visits_last_7": visits_last_7,
        "visits_last_30": visits_last_30,
        "unique_visitors_all": unique_visitors_all,
        "unique_visitors_30": unique_visitors_30,

        # QR totals
        "qr_visits_total": qr_visits_total,
        "qr_visits_30": qr_visits_30,

        # Direct visits
        "direct_visits_total": direct_visits_total,
        "direct_visits_30": direct_visits_30,

        # QR breakdown
        "artists_poster_total": artists_poster_total,
        "audience_poster_total": audience_poster_total,
        "visitcard_total": visitcard_total,
        "artists_poster_30": artists_poster_30,
        "audience_poster_30": audience_poster_30,
        "visitcard_30": visitcard_30,


    }

    return render(request, "admin/kpi_dashboard.html", context)
