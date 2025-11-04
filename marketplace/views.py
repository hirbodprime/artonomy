# marketplace/views.py
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import Http404
from django.db.models import Max

from .models import (
    BusinessProfile,
    JoinRequest,
    Product,
    MarketplaceStats,
)
from .forms import (
    JoinPickKindForm,
    ProfileSetupForm,
    PaymentUploadForm,
)
from accounts.models import Category

# marketplace/views.py  (add below studio_dashboard or replace it)
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.contrib import messages
from .forms import ProductForm

def _get_user_approved_profile_or_none(user):
    return (
        BusinessProfile.objects
        .filter(owner=user, is_approved=True)
        .order_by("-created_at")
        .first()
    )

@login_required
def studio_dashboard(request):
    """
    Landing for approved users. If not approved yet, show wait screen.
    """
    # latest join request (if any)
    jr = (JoinRequest.objects
          .filter(user=request.user)
          .select_related("profile")
          .order_by("-created_at")
          .first())

    approved_profile = _get_user_approved_profile_or_none(request.user)

    if not approved_profile:
        # No approved profile -> show wait (or invite to join if no request)
        if jr and jr.status == JoinRequest.Status.PENDING:
            return render(request, "marketplace/join_wait.html", {"profile": jr.profile, "join_req": jr})
        messages.info(request, _("Start or complete your marketplace application."))
        return redirect("marketplace:join_entry")

    products = approved_profile.products.order_by("-created_at")
    return render(request, "marketplace/dashboard.html", {
        "profile": approved_profile,
        "products": products,
    })

@login_required
def product_create(request):
    profile = _get_user_approved_profile_or_none(request.user)
    if not profile:
        messages.error(request, _("Your profile is not approved yet."))
        return redirect("marketplace:dashboard")

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            prod = form.save(commit=False)
            prod.profile = profile
            prod.save()
            messages.success(request, _("Product created."))
            return redirect("marketplace:dashboard")
    else:
        form = ProductForm(initial={"status": Product.Status.ACTIVE})

    return render(request, "marketplace/product_form.html", {
        "form": form, "is_edit": False
    })

@login_required
def product_edit(request, pk):
    profile = _get_user_approved_profile_or_none(request.user)
    product = get_object_or_404(Product, pk=pk, profile__owner=request.user)
    if not profile or product.profile != profile:
        raise Http404()

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, _("Product updated."))
            return redirect("marketplace:dashboard")
    else:
        form = ProductForm(instance=product)

    return render(request, "marketplace/product_form.html", {
        "form": form, "is_edit": True, "product": product
    })

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, profile__owner=request.user)
    product.delete()
    messages.success(request, _("Product deleted."))
    return redirect("marketplace:dashboard")

# ----------------------
# PUBLIC HOMEPAGE
# ----------------------
def marketplace_home(request):
    """
    Home:
    - Approved business profiles (galleries, artists, etc.)
    - Top products by views
    - Filters: search, category, type (service vs physical)
    - Join Marketplace CTA with counter
    """

    # for header CTA counter
    stats_obj, _ = MarketplaceStats.objects.get_or_create(name="global")
    join_clicks = stats_obj.join_clicks

    # filters
    q = (request.GET.get("q") or "").strip()
    cat_slug = (request.GET.get("cat") or "").strip()
    kind_filter = (request.GET.get("kind") or "").strip()  # SOLO_ARTIST / GALLERY / ...
    prod_type = (request.GET.get("type") or "").strip()    # "service" / "physical"

    # Approved profiles
    profiles_qs = BusinessProfile.objects.filter(is_approved=True)

    if kind_filter:
        profiles_qs = profiles_qs.filter(kind=kind_filter)

    if q:
        profiles_qs = profiles_qs.filter(
            Q(display_name__icontains=q) |
            Q(tagline__icontains=q) |
            Q(bio_long__icontains=q) |
            Q(location__icontains=q)
        )

    # Show a few profiles (no pagination or light pagination)
    profiles_qs = profiles_qs.order_by("-created_at")[:12]

    # Products
    products_qs = Product.objects.filter(
        status=Product.Status.ACTIVE,
        profile__is_approved=True,
    ).select_related("profile", "category")

    if cat_slug:
        products_qs = products_qs.filter(category__slug=cat_slug)

    if prod_type == "service":
        products_qs = products_qs.filter(is_service=True)
    elif prod_type == "physical":
        products_qs = products_qs.filter(is_service=False)

    if q:
        products_qs = products_qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(profile__display_name__icontains=q)
        )

    # Top by views for homepage showcase
    products_qs = products_qs.order_by("-views", "-id")

    paginator = Paginator(products_qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    categories = Category.objects.order_by("name")
    user_join_status = None
    user_approved_profile = None
    if request.user.is_authenticated:
        jr = (
            JoinRequest.objects
            .filter(user=request.user)
            .select_related("profile")
            .order_by("-created_at")
            .first()
        )
        if jr:
            user_join_status = jr.status
            if jr.status == JoinRequest.Status.APPROVED and jr.profile.is_approved:
                user_approved_profile = jr.profile
    ctx = {
        "nav_active": "marketplace",
        "join_clicks": join_clicks,
        "profiles": profiles_qs,
        "products": page_obj,
        "page_obj": page_obj,
        "categories": categories,
        "active_category_slug": cat_slug,
        "search_q": q,
        "kind_filter": kind_filter,
        "prod_type": prod_type,
        "current_query": request.GET.urlencode(),
        "user_join_status": user_join_status,         # None / "PENDING" / "APPROVED" / "REJECTED"
        "user_approved_profile": user_approved_profile,  # BusinessProfile or None

    }
    return render(request, "marketplace/home.html", ctx)


# ----------------------
# JOIN FLOW
# ----------------------

@login_required
def join_marketplace_entry(request):
    """
    Clicked 'Join the Marketplace'.
    - If they already have a PENDING request: show wait screen.
    - If APPROVED: go to dashboard.
    - Else: start wizard.
    """
    # latest request for this user (if any)
    jr = (
        JoinRequest.objects
        .filter(user=request.user)
        .select_related("profile")
        .order_by("-created_at")
        .first()
    )
    if jr:
        if jr.status == JoinRequest.Status.PENDING:
            # don't bump the counter more than necessary, but it's ok if you want:
            # MarketplaceStats.bump_join_clicks()
            return render(request, "marketplace/join_wait.html", {
                "profile": jr.profile,
                "join_req": jr,
            })
        if jr.status == JoinRequest.Status.APPROVED and jr.profile.is_approved:
            messages.info(request, _("You're already approved. Welcome to your studio!"))
            return redirect("marketplace:dashboard")

    # no blocking request -> proceed
    MarketplaceStats.bump_join_clicks()
    request.session.setdefault("market_join", {})
    return redirect(reverse("marketplace:join_steps"))

@login_required
def join_marketplace_steps(request):
    """
    Wizard with guards so a user can't start duplicates,
    but can continue to payment after creating a pending JoinRequest.
    """
    step = int(request.GET.get("step") or request.POST.get("step") or 1)
    data = request.session.get("market_join", {})

    # Only block at step 1 (starting fresh). If the user is mid-flow (step 2/3),
    # allow them to proceed even if there is a PENDING JoinRequest.
    if step == 1:
        existing = (
            JoinRequest.objects
            .filter(user=request.user)
            .select_related("profile")
            .order_by("-created_at")
            .first()
        )
        if existing:
            if existing.status == JoinRequest.Status.PENDING:
                return render(request, "marketplace/join_wait.html", {
                    "profile": existing.profile,
                    "join_req": existing,
                })
            if existing.status == JoinRequest.Status.APPROVED and existing.profile.is_approved:
                messages.info(request, _("You're already approved."))
                return redirect("marketplace:dashboard")


    # We require kind from step 1
    if "kind" not in data:
        return redirect(f"{reverse('marketplace:join_steps')}?step=1")

    # -------------
    # STEP 2: profile setup
    # -------------
    if step == 2:
        # Build or edit a draft BusinessProfile object in memory (not saved yet)
        # We'll store everything temporarily in session here:
        initial = {
            "display_name": data.get("display_name", ""),
            "tagline": data.get("tagline", ""),
            "bio_long": data.get("bio_long", ""),
            "location": data.get("location", ""),
        }

        # Note: avatar/cover are files, can't prefill from session
        if request.method == "POST":
            form = ProfileSetupForm(request.POST, request.FILES, initial=initial)
            if form.is_valid():
                cd = form.cleaned_data
                data["display_name"] = cd["display_name"]
                data["tagline"]      = cd["tagline"]
                data["bio_long"]     = cd["bio_long"]
                data["location"]     = cd["location"]
                # We'll actually CREATE/SAVE BusinessProfile now so we can store media
                profile = BusinessProfile.objects.create(
                    owner=request.user,
                    kind=data["kind"],
                    display_name=cd["display_name"],
                    tagline=cd["tagline"],
                    bio_long=cd["bio_long"],
                    location=cd["location"],
                    is_approved=False,
                )
                # save avatar/cover if provided
                avatar = cd.get("avatar")
                cover  = cd.get("cover")
                updated_fields = []
                if avatar:
                    profile.avatar = avatar
                    updated_fields.append("avatar")
                if cover:
                    profile.cover = cover
                    updated_fields.append("cover")
                if updated_fields:
                    profile.save(update_fields=updated_fields)

                data["profile_id"] = profile.id
                request.session["market_join"] = data

                # also create JoinRequest in PENDING if not exists
                jr, created = JoinRequest.objects.get_or_create(
                    user=request.user,
                    profile=profile,
                    defaults={
                        "status": JoinRequest.Status.PENDING,
                    }
                )

                return redirect(f"{reverse('marketplace:join_steps')}?step=3")
        else:
            form = ProfileSetupForm(initial=initial)

        return render(request, "marketplace/join_step2_profile.html", {
            "step": 2,
            "form": form,
            "kind_choice": data["kind"],
        })

    # -------------
    # STEP 3: payment upload
    # -------------
    if step == 3:
        profile_id = data.get("profile_id")
        if not profile_id:
            # no profile saved yet -> go back
            return redirect(f"{reverse('marketplace:join_steps')}?step=2")

        profile = get_object_or_404(BusinessProfile, id=profile_id, owner=request.user)
        join_req = get_object_or_404(JoinRequest, profile=profile, user=request.user)

        form = PaymentUploadForm(request.POST or None, request.FILES or None, instance=join_req)

        if request.method == "POST" and form.is_valid():
            form.save()
            messages.success(
                request,
                _("Your request has been submitted. Please wait for admin approval.")
            )
            # cleanup: we can clear session so they can restart later if needed
            request.session.pop("market_join", None)
            return render(request, "marketplace/join_wait.html", {
                "profile": profile,
                "join_req": join_req,
            })

        return render(request, "marketplace/join_step3_payment.html", {
            "step": 3,
            "form": form,
            "profile": profile,
            "join_req": join_req,
            # You can also include bank card / IBAN info here, hard-coded or from settings
            "bank_info": {
                "title": _("Payment Information"),
                "card_number": "1234 5678 9012 3456",
                "note": _("Send the subscription fee and upload the screenshot."),
            },
        })

    # fallback
    return redirect(reverse("marketplace:home"))


# ----------------------
# PUBLIC PROFILE PAGE
# ----------------------

def profile_public(request, slug):
    profile = get_object_or_404(
        BusinessProfile.objects.select_related("owner"),
        slug=slug
    )

    if not profile.is_approved:
        # Only owner or staff can see unapproved
        if not request.user.is_authenticated or (
            not request.user.is_staff and request.user != profile.owner
        ):
            raise Http404()

    # bump product views happens in product_detail, not here

    products = profile.products.filter(status=Product.Status.ACTIVE).order_by("-views", "-id")
    return render(request, "marketplace/profile_public.html", {
        "profile": profile,
        "products": products,
    })


# ----------------------
# PRODUCT DETAIL PAGE
# ----------------------

def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related("profile", "profile__owner", "category"),
        pk=pk
    )

    # hide if parent profile isn't approved publicly
    if not product.profile.is_approved:
        if not request.user.is_authenticated or (
            not request.user.is_staff and request.user != product.profile.owner
        ):
            raise Http404()

    # bump views
    Product.objects.filter(pk=product.pk).update(views=F("views") + 1)

    return render(request, "marketplace/product_detail.html", {
        "product": product,
    })


# ----------------------
# DASHBOARD (placeholder)
# ----------------------


