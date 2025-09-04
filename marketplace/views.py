from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

# ⬇️ CHANGED: categories now come from posts app
from posts.models import Category           # <-- adjust app label if needed
from .models import MarketItem, MarketFavorite
from decimal import Decimal
from django.db.models import Q, F, Value, IntegerField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render,redirect

from posts.models import Category
from .models import MarketItem
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .forms import Step1CategoryForm, Step2DetailsForm, Step3PricingMediaForm, Step4ConfirmForm


def marketplace_list(request):
    qs = (
        MarketItem.objects
        .select_related("seller", "seller__profile", "category")
        .filter(status=MarketItem.Status.ACTIVE)
    )

    # --- Filters ---
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

    # numeric filters (ignore malformed)
    try:
        if price_min:
            qs = qs.filter(price__gte=Decimal(price_min))
        if price_max:
            qs = qs.filter(price__lte=Decimal(price_max))
    except Exception:
        pass

    # Popularity = favorites + views
    qs = qs.annotate(
        popularity=Coalesce(F("favorites"), Value(0, output_field=IntegerField())) +
                   Coalesce(F("views"), Value(0, output_field=IntegerField()))
    )

    # --- Sort ---
    if sort == "price_asc":
        qs = qs.order_by("price", "-created_at")
    elif sort == "price_desc":
        qs = qs.order_by("-price", "-created_at")
    elif sort == "popular":
        qs = qs.order_by("-popularity", "-created_at")
    else:  # latest
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
        pk=pk, status=MarketItem.Status.ACTIVE
    )
    # increment views
    MarketItem.objects.filter(pk=item.pk).update(views=F("views") + 1)

    return render(request, "marketplace/item.html", {
        "nav_active": "marketplace",
        "item": item,
    })


@login_required
def toggle_favorite(request, pk):
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

    # Back navigation
    if request.method == "POST" and request.POST.get("nav") == "back":
        step = max(1, step - 1)

    # STEP 1 — Category (store only category_id)
    if step == 1:
        initial = {}
        if data.get("s1", {}).get("category_id"):
            initial["category"] = data["s1"]["category_id"]
        form = Step1CategoryForm(request.POST or None, initial=initial)
        if request.method == "POST" and request.POST.get("nav") == "next" and form.is_valid():
            data["s1"] = {
                "category_id": form.cleaned_data["category"].pk
            }
            _wiz_set(request, data)
            return redirect(f"{reverse('marketplace:add')}?step=2")

    # STEP 2 — Details (strings are fine)
    elif step == 2:
        form = Step2DetailsForm(request.POST or None, initial=data.get("s2"))
        if request.method == "POST" and request.POST.get("nav") == "next" and form.is_valid():
            data["s2"] = {
                "title": form.cleaned_data["title"],
                "description": form.cleaned_data["description"],
            }
            _wiz_set(request, data)
            return redirect(f"{reverse('marketplace:add')}?step=3")

    # STEP 3 — Pricing & Media (store price as string, not Decimal)
    # views.py (snippet)
    elif step == 3:
        initial = {}
        if data.get("s3"):
            if "price" in data["s3"]:
                initial["price"] = Decimal(data["s3"]["price"])
            if "currency" in data["s3"]:
                initial["currency"] = data["s3"]["currency"]
            else:
                initial["currency"] = "TOMAN"  # ✅ default if missing
        else:
            initial["currency"] = "TOMAN"      # ✅ default the very first time

        form = Step3PricingMediaForm(request.POST or None, request.FILES or None, initial=initial)

        if request.method == "POST" and request.POST.get("nav") == "next" and form.is_valid():
            cleaned = form.cleaned_data.copy()
            cleaned.pop("image", None)  # don't keep files in session
            data["s3"] = {
                "price": str(cleaned["price"]),
                "currency": cleaned.get("currency") or "TOMAN",  # ✅ safety
            }
            _wiz_set(request, data)
            request.session[f"{WZ_SESSION_KEY}_has_image"] = "image" in (form.files or {})
            return redirect(f"{reverse('marketplace:add')}?step=4")


    # STEP 4 — Review & Publish (rehydrate everything)
    else:
        form = Step4ConfirmForm(request.POST or None, initial=data.get("s4"))
        if request.method == "POST" and request.POST.get("nav") == "finish" and form.is_valid():
            s1, s2, s3 = data.get("s1"), data.get("s2"), data.get("s3")
            if not (s1 and s2 and s3):
                messages.error(request, "Form session expired. Please start again.")
                return redirect(f"{reverse('marketplace:add')}?step=1")

            category = get_object_or_404(Category, pk=s1["category_id"])
            price = Decimal(s3["price"])

            # views.py (inside step 4 "finish")
            item = MarketItem.objects.create(
                seller=request.user,
                category=category,
                title=s2["title"],
                description=s2["description"],
                price=price,
                currency=s3.get("currency", "TOMAN"),  # ✅ safety net
                status=MarketItem.Status.ACTIVE if form.cleaned_data.get("publish") else MarketItem.Status.DRAFT,
            )


            # attach image if provided in final POST
            image_file = request.FILES.get("image")
            if image_file:
                item.image = image_file
                item.save(update_fields=["image"])

            _wiz_clear(request)
            messages.success(request, "Your service has been created.")
            return redirect("marketplace:item", pk=item.pk)

    # progress indicators & display helpers
    progress = [
        {"num": 1, "label": "Category"},
        {"num": 2, "label": "Details"},
        {"num": 3, "label": "Pricing & Media"},
        {"num": 4, "label": "Review & Publish"},
    ]

    # For the review step, fetch category for display
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
