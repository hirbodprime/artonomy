# portfolio/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.mail import send_mail
from django.views.decorators.http import require_POST

from .models import (
    PortfolioTheme, UserPortfolio, Profile, SocialLink,
    StatCounter, Skill, Education, Experience, Artwork, ServiceItem, Testimonial,
    ThemeLicense,
)
from .forms import (
    ProfileForm, make_sociallink_formset, PublishChoicesForm,
    CounterFS, SkillFS, EducationFS, ExperienceFS, ArtworkFS, ServiceFS, TestimonialFS
)

from decimal import Decimal
from django.db.models import Q, Max
from django.urls import reverse
@login_required
def theme_gallery(request):
    themes = PortfolioTheme.objects.filter(is_active=True).order_by("name")

    owned = set()
    active_theme_id = None
    theme_site_map = {}   # theme_id -> site_id (for the current user)

    if request.user.is_authenticated:
        owned = set(
            ThemeLicense.objects.filter(user=request.user)
            .values_list("theme_id", flat=True)
        )
        # map the user's existing sites by theme
        user_sites = UserPortfolio.objects.filter(user=request.user).only("id", "theme_id", "is_primary", "updated_at")
        theme_site_map = {s.theme_id: s.id for s in user_sites}
        primary = user_sites.filter(is_primary=True).first()
        active_theme_id = primary.theme_id if primary else None

    for t in themes:
        t.is_free_ui = (not t.is_premium) or (t.price_cents == 0)
        t.is_owned_ui = (t.id in owned)
        t.is_active_theme_ui = (active_theme_id == t.id)
        t.display_price = (Decimal(t.price_cents) / Decimal("100")).quantize(Decimal("0.01"))

        # If the user already has a site for this theme, prepare a POST target to make it active
        t.make_active_url = None
        if request.user.is_authenticated and t.id in theme_site_map and not t.is_active_theme_ui:
            site_id = theme_site_map[t.id]
            t.make_active_url = reverse("portfolio:set_primary_portfolio", args=[site_id])

    ctx = {
        "themes": themes,
        "nav_active": "portfolio",
        "owned_theme_ids": owned,
        "theme_site_map": theme_site_map,  # optional, kept for other UI conditions
    }
    return render(request, "portfolio/theme_gallery.html", ctx)


def theme_demo(request, slug):
    theme = get_object_or_404(PortfolioTheme, slug=slug, is_active=True)
    return render(request, f"themes/{theme.slug}/demo.html",{"nav_active":"portfolio"})

from django.db import transaction

@login_required
def theme_select(request, slug):
    """
    Pick a theme for the user. If they already have a portfolio with this theme,
    don't create another one—just reuse it.
    Premium themes still require a license.
    """
    theme = get_object_or_404(PortfolioTheme, slug=slug, is_active=True)

    # Check access (license for premium)
    if not UserPortfolio.user_has_access(request.user, theme):
        messages.warning(request, "This template is premium. Please unlock it to continue.")
        return redirect("portfolio:upgrade_theme", slug=theme.slug)

    # If a site with this theme already exists, reuse it
    existing = (UserPortfolio.objects
                .filter(user=request.user, theme=theme)
                .order_by("-updated_at", "-id")
                .first())
    if existing:
        # If user has no primary yet, make this one primary
        if not UserPortfolio.objects.filter(user=request.user, is_primary=True).exists():
            existing.is_primary = True
            existing.save(update_fields=["is_primary", "updated_at"])
        messages.info(request, f'You already have a "{theme.name}" portfolio. Opening it.')
        return redirect("portfolio:onboarding")

    # Otherwise create a fresh site
    with transaction.atomic():
        make_primary = not UserPortfolio.objects.filter(user=request.user, is_primary=True).exists()
        site = UserPortfolio.objects.create(
            user=request.user,
            theme=theme,
            title=theme.name,
            is_primary=make_primary,
        )

    messages.success(request, f'Created portfolio with theme “{theme.name}”.')
    return redirect("portfolio:onboarding")


@login_required
def upgrade_theme(request, slug):
    """
    Simple purchase page for a single theme. Replace the POST with your Stripe checkout.
    """
    theme = get_object_or_404(PortfolioTheme, slug=slug, is_active=True)

    if UserPortfolio.user_has_access(request.user, theme):
        messages.info(request, "You already have access to this theme.")
        return redirect("portfolio:theme_gallery")

    if request.method == "POST":
        # TODO: integrate Stripe/PayPal; after successful charge, create license:
        ThemeLicense.objects.get_or_create(user=request.user, theme=theme)
        messages.success(request, f"You now own “{theme.name}”. Create a portfolio with it!")
        return redirect("portfolio:theme_select", slug=theme.slug)

    return render(request, "portfolio/upgrade_theme.html", {"theme": theme,"nav_active":"portfolio"})

@login_required
def my_portfolios(request):
    sites = UserPortfolio.objects.filter(user=request.user).select_related("theme")
    ctx = {
        "sites": sites,
        "nav_active": "portfolio",

        "free_max": getattr(settings, "PORTFOLIO_FREE_MAX", None),  # optional
    }
    return render(request, "portfolio/my_portfolios.html", ctx)

from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods

@login_required
@require_http_methods(["GET", "POST"])
def set_primary_portfolio(request, site_id):
    # Harmlessly ignore GETs (don’t mutate)
    if request.method == "GET":
        messages.info(request, "Use the Set Primary button to change your active site.")
        return redirect(request.META.get("HTTP_REFERER") or "portfolio:my_portfolios")

    # POST: do the actual change
    site = get_object_or_404(UserPortfolio, id=site_id, user=request.user)
    UserPortfolio.objects.filter(user=request.user, is_primary=True).exclude(pk=site.pk).update(is_primary=False)
    site.is_primary = True
    site.save(update_fields=["is_primary", "updated_at"])
    messages.success(request, f'"{site.title or site.theme.name}" is now your active portfolio.')
    return redirect(request.META.get("HTTP_REFERER") or "portfolio:my_portfolios")


@login_required
def onboarding(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    SocialLinkFS = make_sociallink_formset()

    profile_form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    link_formset = SocialLinkFS(request.POST or None, instance=profile, prefix="links")
    publish_form = PublishChoicesForm(request.POST or None, user=user)

    counters_fs = CounterFS(request.POST or None, queryset=StatCounter.objects.filter(owner=user), prefix="counters")
    skills_fs   = SkillFS(request.POST or None, queryset=Skill.objects.filter(owner=user), prefix="skills")
    edus_fs     = EducationFS(request.POST or None, queryset=Education.objects.filter(owner=user), prefix="edus")
    exps_fs     = ExperienceFS(request.POST or None, queryset=Experience.objects.filter(owner=user), prefix="exps")
    arts_fs     = ArtworkFS(request.POST or None, request.FILES or None, queryset=Artwork.objects.filter(owner=user), prefix="arts")
    svcs_fs     = ServiceFS(request.POST or None, queryset=ServiceItem.objects.filter(owner=user), prefix="svcs")
    tests_fs    = TestimonialFS(request.POST or None, request.FILES or None, queryset=Testimonial.objects.filter(owner=user), prefix="tests")

    formsets = dict(
        counters_fs=counters_fs, skills_fs=skills_fs, edus_fs=edus_fs, exps_fs=exps_fs,
        arts_fs=arts_fs, svcs_fs=svcs_fs, tests_fs=tests_fs, link_formset=link_formset
    )

    if request.method == "POST":
        ok = profile_form.is_valid() and link_formset.is_valid() and publish_form.is_valid()
        ok = ok and all(getattr(fs, "is_valid", lambda: True)() for fs in formsets.values())
        if ok:
            profile_form.save()
            link_formset.save()

            # Save all model formsets and force owner
            for fs in [counters_fs, skills_fs, edus_fs, exps_fs, arts_fs, svcs_fs, tests_fs]:
                # Get new/changed objects without committing
                objs = fs.save(commit=False)

                for o in objs:
                    # If the model has an owner FK, force it to the current user
                    if hasattr(o, "owner_id"):
                        o.owner_id = user.id  # set the FK directly (avoids deferred assignments)
                    elif hasattr(o, "owner"):
                        o.owner = user
                    o.save()

                # Process deletions
                for o in getattr(fs, "deleted_objects", []):
                    o.delete()

                # In case any form has m2m fields
                if hasattr(fs, "save_m2m"):
                    fs.save_m2m()

            messages.success(request, "Portfolio content saved.")
            return redirect("portfolio:public_portfolio", username=user.username)

    ctx = {"profile_form": profile_form, "publish_form": publish_form, **formsets,"nav_active": "portfolio"}
    return render(request, "portfolio/onboarding.html", ctx)

def public_portfolio(request, username):
    from django.contrib.auth import get_user_model
    U = get_user_model().objects.get(username=username)

    # Prefer the explicit primary; otherwise fall back to most recently updated site
    site = (UserPortfolio.objects
            .filter(user=U, is_primary=True)
            .select_related("theme")
            .first())
    if not site:
        site = (UserPortfolio.objects
                .filter(user=U)
                .select_related("theme")
                .order_by("-is_primary", "-updated_at", "-id")
                .first())

    theme_slug = site.theme.slug if site else "MyPage"

    P = Profile.objects.filter(user=U).first()
    L = P.social_links.all() if P else []
    titles = [t.strip() for t in (P.title or "").split("|") if t.strip()] or [U.get_full_name() or U.username]

    counters = StatCounter.objects.filter(owner=U)
    skills = list(Skill.objects.filter(owner=U).order_by("-percent", "name"))
    # Split skills into two columns to avoid complex template slicing
    SkillsLeft  = skills[::2]
    SkillsRight = skills[1::2]

    edus = Education.objects.filter(owner=U)
    exps = Experience.objects.filter(owner=U)
    arts = list(Artwork.objects.filter(owner=U, is_published=True).order_by("-created_at")[:24])
    svcs = ServiceItem.objects.filter(owner=U).order_by("id")
    tests = Testimonial.objects.filter(owner=U)

    # Categories (optional field) for filter pills — safely handle missing attribute
    Categories = sorted({
        (getattr(a, "category", "") or "").strip()
        for a in arts
        if getattr(a, "category", None)
    })

    cover_url = (P.cover.url if (P and P.cover) else None)
    avatar_url = (P.avatar.url if (P and P.avatar) else None)
    hero_url = (P.hero_image.url if (P and P.hero_image) else None)

    C = dict(
        U=U, P=P, L=L, Counters=counters,
        Skills=skills, SkillsLeft=SkillsLeft, SkillsRight=SkillsRight,
        Edus=edus, Exps=exps, A=arts, S=svcs, T=tests,
        Titles=titles, cover_url=cover_url, avatar_url=avatar_url, hero_url=hero_url,
        site=site, Categories=Categories,
        is_owner=request.user.is_authenticated and request.user == U,
    )
    return render(request, f"themes/{theme_slug}/portfolio.html", C)


def contact_owner(request, username):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid")
    from django.contrib.auth import get_user_model
    U = get_user_model().objects.get(username=username)

    name = request.POST.get("name"); email = request.POST.get("email")
    subject = request.POST.get("subject"); message = request.POST.get("message")
    if not all([name, email, subject, message]):
        return HttpResponseBadRequest("Missing fields")

    body = f"From: {name} <{email}>\n\n{message}"
    send_mail(
        subject=f"[Portfolio] {subject}",
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[getattr(getattr(U, "profile", None), "email_public", None) or U.email],
        fail_silently=True,
    )
    return HttpResponse("OK")
