# app: marketplace (or whatever app holds Product)
from django.shortcuts import render, get_object_or_404,redirect
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from .models import Product, Service, CURRENCY_CHOICES, ArtPost
from django.db.models import Q, F
from itertools import chain
from django.db import models
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import models

User = get_user_model()

LIST_PAGE_SIZE = 12
@require_POST
@login_required
def artpost_toggle_like(request, pk):
    post = get_object_or_404(
        ArtPost.objects.filter(is_active=True, profile__user__is_active=True),
        pk=pk,
    )

    user = request.user
    if post.likes.filter(pk=user.pk).exists():
        post.likes.remove(user)
        liked = False
    else:
        post.likes.add(user)
        liked = True

    return JsonResponse({
        "liked": liked,
        "total_likes": post.total_likes(),
    })


def services_list(request, username=None):
    qs = Service.objects.filter(is_active=True).select_related("profile__user").order_by(
        "order", "-updated_at", "-id"
    )
    owner = None
    if username:
        owner = get_object_or_404(User, username=username)
        qs = qs.filter(profile__user=owner)

    # 🔹 اگر روی «حذف فیلترها» کلیک شد، ریدایرکت تمیز بدون کوئری‌استرینگ
    if request.GET.get("clear"):
        if username:
            return redirect("user_services", username=username)
        return redirect("services")

    # --- جستجو ---
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(tags__icontains=q)
        )

    # --- فیلترها ---
    pricing_model = request.GET.get("pricing_model", "").strip()
    currency = request.GET.get("currency", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()

    if pricing_model in Service.PricingModel.values:
        qs = qs.filter(pricing_model=pricing_model)

    if currency in dict(CURRENCY_CHOICES):
        qs = qs.filter(currency=currency)

    if min_price:
        try:
            qs = qs.filter(min_price__gte=int(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            qs = qs.filter(max_price__lte=int(max_price))
        except ValueError:
            pass

    # --- صفحه‌بندی ---
    paginator = Paginator(qs, LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    ctx = {
        "page_obj": page_obj,
        "owner": owner,
        "username": username,

        # مقادیر فعلی فیلترها
        "q": q,
        "pricing_model": pricing_model,
        "currency": currency,
        "min_price": min_price,
        "max_price": max_price,

        # برای ساخت <select> ها
        "pricing_model_choices": Service.PricingModel.choices,
        "currency_choices": CURRENCY_CHOICES,
    }
    return render(request, "marketplace/services.html", ctx)

def service_detail(request, slug, pk):
    obj = get_object_or_404(
        Service.objects.prefetch_related('images').select_related("profile__user").filter(
            is_active=True,
            profile__user__is_active=True,
        ),
        pk=pk, slug=slug
    )
    return render(request, "marketplace/service_single.html", {"service": obj})
def artpieces_list(request, username=None):
    # ---- محصولات (برای فروش) ----
    products_qs = Product.objects.filter(is_active=True).select_related("profile__user")

    if username:
        products_qs = products_qs.filter(profile__user__username=username)

    # --- کوئری و فیلترها (برای محصولات) ---
    q = request.GET.get("q", "").strip()
    price_type = request.GET.get("price_type", "").strip()   # fixed / neg
    condition = request.GET.get("condition", "").strip()     # new / used
    currency = request.GET.get("currency", "").strip()       # IRT / IRR
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()

    # حذف فیلترها
    if request.GET.get("clear"):
        if username:
            return redirect("user_artpieces", username=username)
        return redirect("artpieces")

    if q:
        products_qs = products_qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )

    if price_type in Product.PriceType.values:
        products_qs = products_qs.filter(price_type=price_type)

    if condition in Product.Condition.values:
        products_qs = products_qs.filter(condition=condition)

    if currency in dict(CURRENCY_CHOICES):
        products_qs = products_qs.filter(currency=currency)

    if min_price:
        try:
            products_qs = products_qs.filter(price_amount__gte=int(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            products_qs = products_qs.filter(price_amount__lte=int(max_price))
        except ValueError:
            pass

    price_filters_active = any([price_type, currency, min_price, max_price])

    # ---- پست‌های محتوایی (ArtPost) ----
    artposts_qs = ArtPost.objects.filter(is_active=True).select_related("profile__user")
    if username:
        artposts_qs = artposts_qs.filter(profile__user__username=username)

    if q:
        artposts_qs = artposts_qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )

    # اگر فیلتر قیمت هست، منطقیه فقط محصولات را نشان بدیم
    if price_filters_active:
        combined = list(products_qs)
    else:
        combined = list(chain(products_qs, artposts_qs))

    # مرتب‌سازی مطابق متا (order ASC, updated_at DESC, id DESC)
    combined.sort(
        key=lambda obj: (
            obj.order,
            -obj.updated_at.timestamp(),
            -obj.id,
        )
    )

    paginator = Paginator(combined, LIST_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    ctx = {
        "page_obj": page_obj,
        "q": q,
        "username": username,

        "price_type": price_type,
        "condition": condition,
        "currency": currency,
        "min_price": min_price,
        "max_price": max_price,

        "price_type_choices": Product.PriceType.choices,
        "condition_choices": Product.Condition.choices,
        "currency_choices": CURRENCY_CHOICES,
    }
    return render(request, "marketplace/artpieces.html", ctx)
def artpiece_detail(request, slug, pk):
    obj = get_object_or_404(
        Product.objects.select_related("profile__user").filter(
            is_active=True,
            profile__user__is_active=True,
        ),
        pk=pk, slug=slug
    )

    related = (
        Product.objects.filter(
            is_active=True,
            profile=obj.profile
        )
        .exclude(pk=obj.pk)
        .order_by("-updated_at")[:8]
    )

    ctx = {"obj": obj, "related": related}
    return render(request, "marketplace/artpiece-single.html", ctx)

def artpost_detail(request, slug, pk):
    obj = get_object_or_404(
        ArtPost.objects.select_related("profile__user").filter(
            is_active=True,
            profile__user__is_active=True,  # اختیاری
        ),
        pk=pk,
        slug=slug,
    )

    # افزایش تعداد بازدید
    ArtPost.objects.filter(pk=obj.pk).update(views=models.F("views") + 1)
    obj.refresh_from_db(fields=["views"])

    related = (
        ArtPost.objects.filter(is_active=True, profile=obj.profile)
        .exclude(pk=obj.pk)
        .order_by("-updated_at")[:8]
    )

    liked_by_me = False
    if request.user.is_authenticated:
        liked_by_me = obj.likes.filter(pk=request.user.pk).exists()

    ctx = {
        "obj": obj,
        "related": related,
        "liked_by_me": liked_by_me,
    }
    return render(request, "marketplace/artpost-single.html", ctx)
