# marketplace/views.py
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext as _
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import Http404
from django.db.models import Max
from django.utils import timezone

from decimal import Decimal

from .models import (
    BusinessProfile,
    JoinRequest,
    Product,
    MarketplaceStats,
)
from .forms import (
    JoinPickKindForm,
    ProfileSetupForm,
    ProductForm,
)
from accounts.models import Category

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from .models import SubscriptionPayment
from .forms import SubscriptionPaymentForm

def _get_user_approved_profile_or_none(user):
    return (
        BusinessProfile.objects
        .filter(owner=user, is_approved=True, subscription_expires_at__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )


@login_required
def studio_dashboard(request):
    """
    Landing for approved users. If not approved or subscription expired, show guidance.
    """
    jr = (JoinRequest.objects
          .filter(user=request.user)
          .select_related("profile")
          .order_by("-created_at")
          .first())

    approved_profile = _get_user_approved_profile_or_none(request.user)

    if not approved_profile:
        # Maybe they have a profile but expired or not approved
        latest_profile = (BusinessProfile.objects
                          .filter(owner=request.user)
                          .order_by("-created_at")
                          .first())
        ctx = {
            "nav_active": "marketplace",
            "profile": latest_profile,
            "is_expired": bool(latest_profile and not latest_profile.is_subscription_active()) if latest_profile else False,
            "needs_approval": bool(latest_profile and not latest_profile.is_approved) if latest_profile else True,
            "join_req": jr,
        }
        return render(request, "marketplace/join_wait.html", ctx)

    products = approved_profile.products.order_by("-created_at")
    return render(request, "marketplace/dashboard.html", {
        "nav_active": "marketplace",
        "profile": approved_profile,
        "products": products,
    })


@login_required
def product_create(request):
    profile = _get_user_approved_profile_or_none(request.user)
    if not profile:
        messages.error(request, _("Your shop is not live yet. Complete onboarding or renew subscription."))
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
        "form": form, "is_edit": False,
        "nav_active": "marketplace",
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
        "nav_active": "marketplace",
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
    - LIVE business profiles (approved + active subscription)
    - Top products by views from LIVE profiles
    - Filters
    """
    stats_obj, _ = MarketplaceStats.objects.get_or_create(name="global")
    join_clicks = stats_obj.join_clicks

    q = (request.GET.get("q") or "").strip()
    cat_slug = (request.GET.get("cat") or "").strip()
    kind_filter = (request.GET.get("kind") or "").strip()  # SOLO_ARTIST / GALLERY / ...
    prod_type = (request.GET.get("type") or "").strip()    # "service" / "physical"

    now = timezone.now()

    # LIVE profiles (approved + subscription active)
    profiles_qs = BusinessProfile.objects.filter(
        is_approved=True,
        subscription_expires_at__gt=now,
    )

    if kind_filter:
        profiles_qs = profiles_qs.filter(kind=kind_filter)

    if q:
        profiles_qs = profiles_qs.filter(
            Q(display_name__icontains=q) |
            Q(tagline__icontains=q) |
            Q(bio_long__icontains=q) |
            Q(location__icontains=q)
        )

    profiles_qs = profiles_qs.order_by("-created_at")[:12]

    # Products only from LIVE profiles
    products_qs = Product.objects.filter(
        status=Product.Status.ACTIVE,
        profile__is_approved=True,
        profile__subscription_expires_at__gt=now,
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
            if jr.profile.is_live():
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
    - If they already have any request, send to steps (we don't block now).
    - Start wizard.
    """
    MarketplaceStats.bump_join_clicks()
    request.session.setdefault("market_join", {})
    return redirect(f"{reverse('marketplace:join_steps')}?step=1")


@login_required
def join_marketplace_steps(request):
    step = int(request.GET.get("step") or request.POST.get("step") or 1)
    data = request.session.get("market_join", {})

    # ⚙️ NEW: Auto-fill session if user clicked "Pay Monthly Fee"
    if step == 3 and "kind" not in data:
        # find their active profile
        profile = BusinessProfile.objects.filter(owner=request.user, is_approved=True).first()
        if profile:
            data["kind"] = profile.kind
            data["profile_id"] = profile.id
            request.session["market_join"] = data
    from django.db import transaction


    # ---- STEP 1: Choose kind
    if step == 1:
        if request.method == "POST":
            form = JoinPickKindForm(request.POST)
            if form.is_valid():
                data["kind"] = form.cleaned_data["kind"]
                request.session["market_join"] = data
                request.session.modified = True
                return redirect(f"{reverse('marketplace:join_steps')}?step=2")
        else:
            form = JoinPickKindForm(initial={"kind": data.get("kind")})

        return render(request, "marketplace/join_step1_kind.html", {
            "nav_active": "marketplace",
            "step": 1,
            "form": form,
        })

    # From here we need kind
    if "kind" not in data:
        return redirect(f"{reverse('marketplace:join_steps')}?step=1")

    # ---- STEP 2: Profile setup
    if step == 2:
        initial = {
            "display_name": data.get("display_name", ""),
            "tagline": data.get("tagline", ""),
            "bio_long": data.get("bio_long", ""),
            "location": data.get("location", ""),
        }

        if request.method == "POST":
            form = ProfileSetupForm(request.POST, request.FILES, initial=initial)
            if form.is_valid():
                cd = form.cleaned_data

                # Cache basic fields in session (if user returns back)
                data["display_name"] = cd["display_name"]
                data["tagline"]      = cd["tagline"]
                data["bio_long"]     = cd["bio_long"]
                data["location"]     = cd["location"]

                # Create draft profile (not visible until trial starts in step 3)
                profile = BusinessProfile.objects.create(
                    owner=request.user,
                    kind=data["kind"],
                    display_name=cd["display_name"],
                    tagline=cd["tagline"],
                    bio_long=cd["bio_long"],
                    location=cd["location"],
                    is_approved=False,  # will become True when trial starts
                )
                updated_fields = []
                if cd.get("avatar"):
                    profile.avatar = cd["avatar"]; updated_fields.append("avatar")
                if cd.get("cover"):
                    profile.cover = cd["cover"]; updated_fields.append("cover")
                if updated_fields:
                    profile.save(update_fields=updated_fields)

                data["profile_id"] = profile.id
                request.session["market_join"] = data
                request.session.modified = True

                # Create/Update a JoinRequest as APPROVED (we skip payment now)
                with transaction.atomic():
                    jr = (
                        JoinRequest.objects
                        .select_for_update()
                        .filter(user=request.user)
                        .order_by("-created_at")
                        .first()
                    )
                    if jr:
                        jr.profile = profile
                        jr.status = JoinRequest.Status.APPROVED
                        jr.save(update_fields=["profile", "status"])
                    else:
                        JoinRequest.objects.create(
                            user=request.user,
                            profile=profile,
                            status=JoinRequest.Status.APPROVED,
                        )

                return redirect(f"{reverse('marketplace:join_steps')}?step=3")
        else:
            form = ProfileSetupForm(initial=initial)

        return render(request, "marketplace/join_step2_profile.html", {
            "nav_active": "marketplace",
            "step": 2,
            "form": form,
            "kind_choice": data["kind"],
        })

    # ---- STEP 3: Start 2-day free trial + success
    if step == 3:
        profile_id = data.get("profile_id")
        if not profile_id:
            return redirect(f"{reverse('marketplace:join_steps')}?step=2")

        profile = get_object_or_404(BusinessProfile, id=profile_id, owner=request.user)

        # Only start trial if nothing is active
        if not profile.is_subscription_active():
            profile.start_free_trial(days=2, auto_approve=True)

        approved_payment_exists = SubscriptionPayment.objects.filter(
            profile=profile,
            status=SubscriptionPayment.Status.APPROVED
        ).exists()

        payments = list(profile.subscription_payments.all()[:10])

        request.session.pop("market_join", None)

        return render(request, "marketplace/join_step3_trial_started.html", {
            "profile": profile,
            "state": profile.subscription_state(),   # 👈 pass state explicitly
            "approved_payment_exists": approved_payment_exists,
            "payments": payments,
        })

    # Fallback
    return redirect(reverse("marketplace:home"))





from .models import (
    BusinessProfile, JoinRequest, Product, MarketplaceStats, SubscriptionPayment
)
from .forms import (
    JoinPickKindForm, ProfileSetupForm, ProductForm, SubscriptionPaymentForm
)
from django.contrib.auth.decorators import user_passes_test

@login_required
def subscription_pay(request):
    profile = (BusinessProfile.objects
               .filter(owner=request.user)
               .order_by("-created_at")
               .first())
    if not profile:
        messages.error(request, _("Please complete your profile first."))
        return redirect("marketplace:join_steps")

    bank_info = {
        "title": _("Marketplace Billing"),
        "card_number": "6219-8619-4904-7871",
        "note": _("Send exact amount. Upload your receipt here. We'll review ASAP."),
    }

    if request.method == "POST":
        form = SubscriptionPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            sp = form.save(commit=False)
            sp.profile = profile
            sp.status = SubscriptionPayment.Status.PENDING
            sp.currency = "TOMAN"           # optional default
            sp.months_granted = 1           # default month
            sp.save()
            messages.success(request, _("Payment submitted. We’ll notify you after review."))
            return redirect("marketplace:subscription_pay")
        else:
            messages.error(request, _("Please fix the errors below."))
    else:
        form = SubscriptionPaymentForm()

    payments = profile.subscription_payments.all()[:10]

    ctx = {
        "nav_active": "marketplace",
        "profile": profile,
        "expires_at": profile.subscription_expires_at,   # real expiry (trial or paid)
        "approved_payment_exists": profile.subscription_payments
                                    .filter(status="APPROVED").exists(),
        "bank_info": bank_info,
        "form": form,
        "payments": payments,
    }
    return render(request, "marketplace/join_step3_payment.html", ctx)




@user_passes_test(lambda u: u.is_staff)
def payment_review(request, pk, action):
    sp = get_object_or_404(SubscriptionPayment.objects.select_related("profile"), pk=pk)
    if action == "approve":
        sp.approve(request.user)
        messages.success(request, _("Payment approved and subscription extended."))
    elif action == "reject":
        note = request.GET.get("note", "")
        sp.reject(request.user, note=note)
        messages.warning(request, _("Payment rejected."))
    else:
        messages.error(request, _("Unknown action."))
    # send the admin back where they came from or to the payment page for that user
    return redirect(request.META.get("HTTP_REFERER") or reverse("marketplace:subscription_pay"))

@staff_member_required
def payments_inbox(request):
    qs = (SubscriptionPayment.objects
          .select_related("user", "profile")
          .order_by("status", "-created_at"))
    return render(request, "marketplace/payments_inbox.html", {"payments": qs})


@staff_member_required
def payment_approve(request, pk):
    pay = get_object_or_404(SubscriptionPayment, pk=pk)
    if request.method == "POST":
        note = request.POST.get("note", "")
        months = int(request.POST.get("months") or "1")
        pay.approve(request.user, months=months, note=note)
        messages.success(request, _("Payment approved. Subscription extended."))
    return redirect("marketplace:payments_inbox")


@staff_member_required
def payment_reject(request, pk):
    pay = get_object_or_404(SubscriptionPayment, pk=pk)
    if request.method == "POST":
        note = request.POST.get("note", "")
        pay.reject(request.user, note=note)
        messages.warning(request, _("Payment rejected."))
    return redirect("marketplace:payments_inbox")

# ----------------------
# PUBLIC PROFILE PAGE
# ----------------------
def profile_public(request, slug):
    profile = get_object_or_404(
        BusinessProfile.objects.select_related("owner"),
        slug=slug
    )

    # Only visible if approved + active subscription
    if not profile.is_live():
        raise Http404()

    products = profile.products.filter(status=Product.Status.ACTIVE).order_by("-views", "-id")
    return render(request, "marketplace/profile_public.html", {
        "nav_active": "marketplace",
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

    # hide if parent profile isn't LIVE
    if not product.profile.is_live():
        raise Http404()

    # bump views
    Product.objects.filter(pk=product.pk).update(views=F("views") + 1)

    return render(request, "marketplace/product_detail.html", {
        "nav_active": "marketplace",
        "product": product,
    })
