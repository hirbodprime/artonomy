# marketplace/views.py
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, F, Value, IntegerField, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse

from posts.models import Category
from .models import MarketItem, MarketFavorite
from .forms import (
    Step1CategoryForm, Step2DetailsForm, Step3PricingForm, Step4ConfirmForm
)

# ---- Public list ----
def marketplace_list(request):
    qs = (
        MarketItem.objects
        .select_related("seller", "seller__profile", "category")
        .filter(status=MarketItem.Status.ACTIVE)
    )

    # Filters
    q = (request.GET.get("q") or "").strip()
    cat_slug = (request.GET.get("cat") or "").strip()
    price_min = (request.GET.get("min") or "").strip()
    price_max = (request.GET.get("max") or "").strip()
    sort = (request.GET.get("sort") or "latest").lower()

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(seller__username__icontains=q)
        )

    active_category = None
    if cat_slug:
        qs = qs.filter(category__slug=cat_slug)
        active_category = Category.objects.filter(slug=cat_slug).first()

    # Unify price for filtering/sorting:
    # effective_min = price for FIXED; price_min for RANGE; 0 for NEGOTIABLE
    # effective_max = price for FIXED; price_max for RANGE; very high for NEGOTIABLE (we’ll just use price as 0 and ignore negotiable in strict numeric filters)
    qs = qs.annotate(
        # popularity for sorting
        popularity=Coalesce(F("favorites"), Value(0, output_field=IntegerField())) +
                   Coalesce(F("views"), Value(0, output_field=IntegerField())),
        # effective min/max
        eff_min=Coalesce(
            # RANGE min
            Coalesce('price_min', Value(None, output_field=DecimalField())),
            # FIXED price as min when range min absent
            Coalesce('price', Value(0, output_field=DecimalField())),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        ),
        eff_max=Coalesce(
            # RANGE max
            Coalesce('price_max', Value(None, output_field=DecimalField())),
            # FIXED price as max when range max absent
            Coalesce('price', Value(0, output_field=DecimalField())),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        )
    )

    # Numeric filters—apply only to FIXED/RANGE meaningfully.
    # Negotiable (with price=0 and no min/max) will generally pass only if bounds include 0.
    try:
        if price_min:
            qs = qs.filter(
                Q(pricing_type=MarketItem.PricingType.FIXED, price__gte=Decimal(price_min))
                | Q(pricing_type=MarketItem.PricingType.RANGE, price_max__gte=Decimal(price_min))
            )
        if price_max:
            qs = qs.filter(
                Q(pricing_type=MarketItem.PricingType.FIXED, price__lte=Decimal(price_max))
                | Q(pricing_type=MarketItem.PricingType.RANGE, price_min__lte=Decimal(price_max))
            )
    except Exception:
        pass

    # Sort
    if sort == "price_asc":
        qs = qs.order_by("eff_min", "created_at")
    elif sort == "price_desc":
        qs = qs.order_by("-eff_max", "-created_at")
    elif sort == "popular":
        qs = qs.order_by("-popularity", "-created_at")
    else:
        qs = qs.order_by("-created_at")

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    categories = Category.objects.order_by("name")

    ctx = {
        "nav_active": "marketplace",
        "items": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "active_category": active_category,
        "q": q,
        "sort": sort,
        "price_min": price_min,
        "price_max": price_max,
        "current_query": request.GET.urlencode(),
    }
    return render(request, "marketplace/list.html", ctx)


def marketplace_item(request, pk):
    item = get_object_or_404(
        MarketItem.objects.select_related("seller", "seller__profile", "category"),
        pk=pk
    )
    is_owner_or_staff = request.user.is_authenticated and (
        request.user.is_staff or request.user == item.seller
    )
    if not is_owner_or_staff and item.status != MarketItem.Status.ACTIVE:
        raise Http404()

    MarketItem.objects.filter(pk=item.pk).update(views=F("views") + 1)
    return render(request, "marketplace/item.html", {
        "nav_active": "marketplace",
        "item": item,
    })


@login_required
def toggle_favorite(request, pk):
    # Kept for compatibility, but your UI no longer shows the button.
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=400)
    item = get_object_or_404(MarketItem, pk=pk, status=MarketItem.Status.ACTIVE)
    obj, created = MarketFavorite.objects.get_or_create(user=request.user, item=item)
    if not created:
        obj.delete()
        MarketItem.objects.filter(pk=item.pk).update(favorites=F("favorites") - 1)
        return JsonResponse({"ok": True, "favorited": False})
    else:
        MarketItem.objects.filter(pk=item.pk).update(favorites=F("favorites") + 1)
        return JsonResponse({"ok": True, "favorited": True})


# ===== Wizard =====
WZ_SESSION_KEY = "marketitem_wizard"

def _wiz_get(request):
    return request.session.get(WZ_SESSION_KEY, {})

def _wiz_set(request, data):
    request.session[WZ_SESSION_KEY] = data
    request.session.modified = True

def _wiz_clear(request):
    request.session.pop(WZ_SESSION_KEY, None)
    request.session.pop(f"{WZ_SESSION_KEY}_has_image", None)


@login_required
def marketitem_create(request):
    step = int(request.POST.get("step") or request.GET.get("step") or 1)
    data = _wiz_get(request)

    # Back
    if request.method == "POST" and request.POST.get("nav") == "back":
        step = max(1, step - 1)

    # STEP 1 — Category
    if step == 1:
        initial = {}
        if data.get("s1", {}).get("category_id"):
            initial["category"] = data["s1"]["category_id"]
        form = Step1CategoryForm(request.POST or None, initial=initial)
        if request.method == "POST" and request.POST.get("nav") == "next" and form.is_valid():
            data["s1"] = {"category_id": form.cleaned_data["category"].pk}
            _wiz_set(request, data)
            return redirect(f"{reverse('marketplace:add')}?step=2")

    # STEP 2 — Details
    elif step == 2:
        form = Step2DetailsForm(request.POST or None, initial=data.get("s2"))
        if request.method == "POST" and request.POST.get("nav") == "next" and form.is_valid():
            data["s2"] = {
                "title": form.cleaned_data["title"],
                "description": form.cleaned_data["description"],
            }
            _wiz_set(request, data)
            return redirect(f"{reverse('marketplace:add')}?step=3")

    # STEP 3 — Pricing (no files here)
    elif step == 3:
        initial = data.get("s3") or {"pricing_type": "NEGOTIABLE", "currency": "TOMAN"}
        form = Step3PricingForm(request.POST or None, initial=initial)
        if request.method == "POST" and request.POST.get("nav") == "next" and form.is_valid():
            cd = form.cleaned_data
            data["s3"] = {
                "pricing_type": cd["pricing_type"],
                "currency": cd.get("currency") or "TOMAN",
            }
            if cd["pricing_type"] == "FIXED":
                data["s3"]["price"] = str(cd["price"])
                data["s3"]["price_min"] = None
                data["s3"]["price_max"] = None
            elif cd["pricing_type"] == "RANGE":
                data["s3"]["price"] = None
                data["s3"]["price_min"] = str(cd["price_min"])
                data["s3"]["price_max"] = str(cd["price_max"])
            else:  # NEGOTIABLE
                data["s3"]["price"] = None
                data["s3"]["price_min"] = None
                data["s3"]["price_max"] = None

            _wiz_set(request, data)
            return redirect(f"{reverse('marketplace:add')}?step=4")

    # STEP 4 — Review & Publish (+ image upload here)
    else:
        form = Step4ConfirmForm(request.POST or None, initial=data.get("s4"))
        if request.method == "POST" and request.POST.get("nav") == "finish" and form.is_valid():
            s1, s2, s3 = data.get("s1"), data.get("s2"), data.get("s3")
            if not (s1 and s2 and s3):
                messages.error(request, "Form session expired. Please start again.")
                return redirect(f"{reverse('marketplace:add')}?step=1")

            category = get_object_or_404(Category, pk=s1["category_id"])

            # Create item based on pricing_type
            pricing_type = s3["pricing_type"]
            kwargs = dict(
                seller=request.user,
                category=category,
                title=s2["title"],
                description=s2["description"],
                pricing_type=pricing_type,
                currency=s3.get("currency", "TOMAN"),
                status=MarketItem.Status.ACTIVE,
            )
            if pricing_type == MarketItem.PricingType.FIXED:
                kwargs["price"] = Decimal(s3["price"])
                kwargs["price_min"] = None
                kwargs["price_max"] = None
            elif pricing_type == MarketItem.PricingType.RANGE:
                kwargs["price"] = Decimal("0")
                kwargs["price_min"] = Decimal(s3["price_min"])
                kwargs["price_max"] = Decimal(s3["price_max"])
            else:  # NEGOTIABLE
                kwargs["price"] = Decimal("0")
                kwargs["price_min"] = None
                kwargs["price_max"] = None

            item = MarketItem.objects.create(**kwargs)

            # attach image from final step
            image_file = request.FILES.get("image")
            if image_file:
                item.image = image_file
                item.save(update_fields=["image"])

            _wiz_clear(request)
            messages.success(request, "Your service has been created.")
            return redirect("marketplace:item", pk=item.pk)

    # Progress & review
    progress = [
        {"num": 1, "label": "Category"},
        {"num": 2, "label": "Details"},
        {"num": 3, "label": "Pricing & Media"},
        {"num": 4, "label": "Review & Publish"},
    ]

    review_category = None
    if data.get("s1", {}).get("category_id"):
        review_category = Category.objects.filter(pk=data["s1"]["category_id"]).first()

    return render(request, "marketplace/add.html", {
        "step": step,
        "form": form,
        "progress": progress,
        "data": data,
        "review_category": review_category,
    })
