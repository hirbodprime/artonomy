# core/views_admin.py
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Q
from django.shortcuts import render
from django.utils import timezone

from accounts.models import Profile
from artists.models import Category, Subcategory
from marketplace.models import Product, Service, ArtPost

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

    premium_q = Profile.premium_q()
    premium_profiles = Profile.objects.filter(premium_q).count()
    trial_only_profiles = Profile.objects.filter(
        premium_q,
        subscription_expires_at__isnull=True,
    ).count()
    paid_sub_profiles = Profile.objects.filter(
        subscription_expires_at__isnull=False,
        subscription_expires_at__gte=now,
    ).count()

    # new users / profiles
    users_last_7 = User.objects.filter(date_joined__gte=week_ago).count() if hasattr(User, "date_joined") else None
    profiles_last_7 = Profile.objects.filter(created_at__gte=week_ago).count()

    # near expiry subs (next 7 days)
    near_expiry_subs = Profile.objects.filter(
        subscription_expires_at__isnull=False,
        subscription_expires_at__gt=now,
        subscription_expires_at__lte=now + timedelta(days=7),
    ).count()

    trial_expired = Profile.objects.filter(
        trial_started_at__isnull=False,
        subscription_expires_at__isnull=True,
    ).exclude(trial_started_at__gte=now - timedelta(days=Profile.TRIAL_DAYS)).count()

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
    latest_premium_profiles = (
        Profile.objects
        .filter(premium_q)
        .select_related("user")
        .order_by("-created_at")[:10]
    )

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
        "premium_profiles": premium_profiles,
        "trial_only_profiles": trial_only_profiles,
        "paid_sub_profiles": paid_sub_profiles,
        "users_last_7": users_last_7,
        "profiles_last_7": profiles_last_7,
        "near_expiry_subs": near_expiry_subs,
        "trial_expired": trial_expired,
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
        "latest_premium_profiles": latest_premium_profiles,
        "latest_products": latest_products,
        "latest_services": latest_services,
        "latest_artposts": latest_artposts,
    }

    return render(request, "admin/kpi_dashboard.html", context)
