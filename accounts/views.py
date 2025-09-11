# accounts/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .onboarding import next_onboarding_step, ROLE_STEP, CATEGORIES_STEP, DONE
from posts.models import Post
from network.models import Follow
from accounts.models import (
    Profile, Education, Experience, Book, Certification, Course, Project, Award,
    SkillTag, SocialLink, PersonalValue, HobbyInterest, Achievement, Goal, FunFact,UserCategory,Category,User,User ,username_validator
)
from suggest.models import Suggestion

from django.contrib.auth import logout
from django.urls import reverse

# accounts/views.py  (additions)
from django.db import transaction
from .forms import (
    ProfileBasicsForm, SkillsCSVForm, ValuesHobbiesForm, FunFactsForm,
    SocialLinkFormSet,
    EducationFS, ExperienceFS, ProjectFS, CertificationFS, CourseFS, AwardFS, BookFS
)
import re
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q, F
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _, get_language


User = get_user_model()

# views.py (signup, clean version)


GMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@gmail\.com$", re.IGNORECASE)

def logout_view(request):
    """Logs out the user and redirects to explore (or login)."""
    logout(request)
    return redirect(reverse("landing"))



def signup_view(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email    = (request.POST.get("email") or "").strip().lower()
        password = (request.POST.get("password") or "")

        # keep previous values to repopulate on error
        ctx = {"prefill": {"username": username, "email": email}}

        # normalize username: only keep [a-zA-Z0-9_], force lowercase
        cleaned_username = re.sub(r'[^a-zA-Z0-9_]', '', username).lower()

        if not cleaned_username:
            messages.error(request, _("Please choose a valid username (letters, numbers, underscores)."))
            return render(request, "accounts/signup.html", ctx)

        try:
            from accounts.models import username_validator  # or import at top
            username_validator(cleaned_username)
        except ValidationError as e:
            messages.error(request, e.message)
            return render(request, "accounts/signup.html", ctx)

        if User.objects.filter(username__iexact=cleaned_username).exists():
            messages.error(request, _("Username already taken."))
            return render(request, "accounts/signup.html", ctx)

        if not email:
            messages.error(request, _("Email is required."))
            return render(request, "accounts/signup.html", ctx)

        # ✅ Gmail-only
        if not GMAIL_PATTERN.match(email):
            messages.error(request, _("Only Gmail addresses are allowed (example: you@gmail.com)."))
            return render(request, "accounts/signup.html", ctx)

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, _("Email already in use."))
            return render(request, "accounts/signup.html", ctx)

        if len(password) < 8:
            messages.error(request, _("Password must be at least 8 characters."))
            return render(request, "accounts/signup.html", ctx)

        # Create user
        user = User.objects.create_user(
            username=cleaned_username,
            email=email,
            password=password,
        )
        if hasattr(user, "email_verified"):
            user.email_verified = False
            user.save(update_fields=["email_verified"])

        login(request, user)
        return redirect("choose_role")

    # GET
    return render(request, "accounts/signup.html")



@login_required
def choose_role(request):
    step = next_onboarding_step(request.user)
    if step != ROLE_STEP:
        # If user isn’t supposed to be here, bounce (middleware also covers it)
        return redirect("explore") if step == DONE else redirect("choose_categories")

    if request.method == "POST":
        role = request.POST.get("role")
        if role in dict(User.Role.choices):
            request.user.role = role
            request.user.save(update_fields=["role"])
            messages.success(request, "Role saved.")
            return redirect("choose_categories")
        messages.error(request, "Please choose a valid option.")
    return render(request, "accounts/choose_role.html")


@login_required
def choose_categories(request):
    step = next_onboarding_step(request.user)
    if step == ROLE_STEP:
        return redirect("choose_role")
    if step == DONE:
        return redirect("explore")

    user = request.user
    rel_kind = UserCategory.Kind.WORK if user.role == User.Role.ARTIST else UserCategory.Kind.FAV

    if request.method == "POST":
        slugs = [s.strip() for s in request.POST.get("selected_slugs", "").split(",") if s.strip()]
        # Accept both English and Persian slugs
        cats = list(Category.objects.filter(Q(slug__in=slugs) | Q(slug_fa__in=slugs)))

        # remove deselected
        UserCategory.objects.filter(user=user, kind=rel_kind).exclude(category__in=cats).delete()

        existing = set(
            UserCategory.objects.filter(user=user, kind=rel_kind).values_list("category_id", flat=True)
        )
        to_create = [
            UserCategory(user=user, category=c, kind=rel_kind)
            for c in cats if c.id not in existing
        ]
        if to_create:
            UserCategory.objects.bulk_create(to_create, ignore_conflicts=True)

        messages.success(request, _("Preferences saved."))
        return redirect("explore")  # onboarding complete

    # Preselect current choices
    chosen_ids = set(
        UserCategory.objects.filter(user=user, kind=rel_kind).values_list("category_id", flat=True)
    )

    # Language-aware ordering for the chooser grid
    lang = (get_language() or "").lower()
    if lang.startswith("fa"):
        categories = Category.objects.annotate(sort_name=Coalesce("name_fa", "name")).order_by("sort_name")
    else:
        categories = Category.objects.all().order_by("name")

    heading_text = _("Your Favorite Categories") if rel_kind == UserCategory.Kind.FAV else _("Your Work Categories")

    return render(request, "accounts/categories.html", {
        "categories": categories,
        "chosen_ids": chosen_ids,
        "rel_kind": rel_kind,
        "heading_text": heading_text,
    })





def profile_view(request, username: str):
    UserModel = get_user_model()
    profile_user = get_object_or_404(
        UserModel.objects.select_related("profile"),
        username=username
    )
    profile = getattr(profile_user, "profile", None) or Profile.objects.create(user=profile_user) if not hasattr(profile_user, "profile") else profile_user.profile

    # follow stats / state
    followers_count = profile_user.follower_relations.count()
    following_count = profile_user.following_relations.count()
    is_following = (
        request.user.is_authenticated
        and request.user != profile_user
        and Follow.objects.filter(follower=request.user, following=profile_user).exists()
    )

    # timeline
    timeline_posts = (
        Post.objects.filter(author=profile_user)
        .select_related("author", "author__profile")
        .prefetch_related("images", "videos", "chapters")
        .order_by("-created_at")
    )

    # personal info
    social_links = profile.social_links.all()
    values       = profile.values.all()
    hobbies      = profile.hobbies.all()
    achievements = profile.achievements.all()
    goals        = profile.goals.all()
    funfacts     = profile.funfacts.all()

    # portfolio (resume)
    educations     = profile.educations.all()
    experiences    = profile.experiences.all()
    skills         = profile.skills.all()
    books          = profile.books.all()
    certifications = profile.certifications.all()
    courses        = profile.courses.all()
    projects       = profile.projects.all()
    awards         = profile.awards.all()

    # marketplace (optional)
    market_items = []
    try:
        from marketplace.models import MarketItem
        market_items = (
            MarketItem.objects.filter(seller=profile_user, status=MarketItem.Status.ACTIVE)
            .select_related("seller", "seller__profile", "category")
            .order_by("-created_at")[:18]
        )
    except Exception:
        pass

    work_cats = Category.objects.filter(
        usercategory__user=profile_user,
        usercategory__kind=UserCategory.Kind.WORK
    ).order_by("name")

    fav_cats = Category.objects.filter(
        usercategory__user=profile_user,
        usercategory__kind=UserCategory.Kind.FAV
    ).order_by("name")

    suggestions_made_count = Suggestion.objects.filter(suggester=profile_user).count()
    suggestions_received_count = Suggestion.objects.filter(post__author=profile_user).count()

    suggested_posts = (
        Post.objects.filter(suggestions__suggester=profile_user)
        .select_related("author", "author__profile")
        .prefetch_related("images", "videos", "chapters")
        .order_by("-suggestions__created_at")
    )

    # ---- language-aware category label + ordering for hero chips ----
    lang = (get_language() or "").lower()
    if profile_user.role == User.Role.ARTIST:
        kind = UserCategory.Kind.WORK
        hero_cats_label = _("Working categories")
    else:
        kind = UserCategory.Kind.FAV
        hero_cats_label = _("Favorite categories")

    if lang.startswith("fa"):
        # order by Persian name if available, else English name
        hero_cats = (
            Category.objects
            .filter(usercategory__user=profile_user, usercategory__kind=kind)
            .annotate(sort_name=Coalesce("name_fa", "name"))
            .order_by("sort_name")[:6]
        )
    else:
        hero_cats = (
            Category.objects
            .filter(usercategory__user=profile_user, usercategory__kind=kind)
            .order_by("name")[:6]
        )

    show_market = (profile_user.role == User.Role.ARTIST)
    is_owner = request.user.is_authenticated and request.user == profile_user

    ctx = {
        "nav_active": None,
        "profile_user": profile_user,
        "profile": profile,
        "show_market": show_market,

        "followers_count": followers_count,
        "following_count": following_count,
        "is_following_author": is_following,

        "timeline_posts": timeline_posts,
        "is_owner": is_owner,

        "social_links": social_links,
        "values": values,
        "hobbies": hobbies,
        "achievements": achievements,
        "goals": goals,
        "funfacts": funfacts,

        "educations": educations,
        "experiences": experiences,
        "skills": skills,
        "books": books,
        "certifications": certifications,
        "courses": courses,
        "projects": projects,
        "awards": awards,

        "market_items": market_items,

        "hero_cats": hero_cats,
        "hero_cats_label": hero_cats_label,
        "suggestions_made_count": suggestions_made_count,
        "suggestions_received_count": suggestions_received_count,
        "suggested_posts": suggested_posts,
    }
    return render(request, "accounts/profile.html", ctx)


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Prefetch
from django.contrib.auth import get_user_model
from posts.models import Post  # adjust if your model path differs

@login_required
def profile_suggested_posts(request, username: str):
    User = get_user_model()
    profile_user = get_object_or_404(
        User.objects.select_related("profile"),
        username=username
    )

    # Posts this user suggested (fast prefetch for media)
    qs = (
        Post.objects
        .filter(suggestions__suggester=profile_user)
        .select_related("author", "author__profile")
        .prefetch_related("images", "videos", "chapters")
        .order_by("-suggestions__created_at", "-created_at")
        .distinct()
    )

    paginator = Paginator(qs, 12)  # 12 cards per page
    page = request.GET.get("page") or 1
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    return render(
        request,
        "accounts/profile_suggested.html",
        {
            "profile_user": profile_user,
            "page_obj": page_obj,
            "total": paginator.count,
        },
    )















# ---------- Edit profile hub ----------
@login_required
def settings_profile_start(request):
    profile = get_object_or_404(Profile, user=request.user)
    return render(request, "accounts/settings_hub.html", {
        "nav_active": None,
        "profile": profile,
    })

# ---------- Personal wizard (6 steps) ----------
PERSONAL_STEPS = [
    "Basics", "Skills", "Values & Hobbies", "Fun facts", "Social links", "Review",
]

@login_required
@transaction.atomic
def settings_personal_wizard(request, step=1):
    step = int(step or 1)
    profile = get_object_or_404(Profile, user=request.user)

    # Step 1: Basics
    if step == 1:
        if request.method == "POST":
            form = ProfileBasicsForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Basics saved.")
                return redirect("settings_personal", step=2)
        else:
            form = ProfileBasicsForm(instance=profile)
        return render(request, "accounts/settings_personal.html", {
            "step": step, "steps": PERSONAL_STEPS, "form": form,
        })

    # Step 2: Skills (CSV)
    if step == 2:
        if request.method == "POST":
            form = SkillsCSVForm(request.POST)
            if form.is_valid():
                csv = form.cleaned_data.get("skills_csv","")
                names = [s.strip() for s in csv.replace("\n", ",").split(",") if s.strip()]
                if names:
                    tags = [SkillTag.objects.get_or_create(name=n)[0] for n in names]
                    profile.skills.set(tags)
                else:
                    profile.skills.clear()
                messages.success(request, "Skills updated.")
                return redirect("settings_personal", step=3)
        else:
            current = ", ".join(profile.skills.values_list("name", flat=True))
            form = SkillsCSVForm(initial={"skills_csv": current})
        return render(request, "accounts/settings_personal.html", {
            "step": step, "steps": PERSONAL_STEPS, "form": form,
        })

    # Step 3: Values & Hobbies
    if step == 3:
        if request.method == "POST":
            form = ValuesHobbiesForm(request.POST)
            if form.is_valid():
                v = [s.strip() for s in form.cleaned_data.get("values_csv","").replace("\n", ",").split(",") if s.strip()]
                h = [s.strip() for s in form.cleaned_data.get("hobbies_csv","").replace("\n", ",").split(",") if s.strip()]
                profile.values.all().delete()
                profile.hobbies.all().delete()
                PersonalValue.objects.bulk_create([PersonalValue(profile=profile, name=x) for x in v])
                HobbyInterest.objects.bulk_create([HobbyInterest(profile=profile, name=x) for x in h])
                messages.success(request, "Values & hobbies saved.")
                return redirect("settings_personal", step=4)
        else:
            v = ", ".join(profile.values.values_list("name", flat=True))
            h = ", ".join(profile.hobbies.values_list("name", flat=True))
            form = ValuesHobbiesForm(initial={"values_csv": v, "hobbies_csv": h})
        return render(request, "accounts/settings_personal.html", {
            "step": step, "steps": PERSONAL_STEPS, "form": form,
        })

    # Step 4: Fun facts
    if step == 4:
        if request.method == "POST":
            form = FunFactsForm(request.POST)
            if form.is_valid():
                txt = form.cleaned_data.get("funfacts_csv","")
                lines = [s.strip() for s in txt.replace(",", "\n").split("\n") if s.strip()]
                profile.funfacts.all().delete()
                FunFact.objects.bulk_create([FunFact(profile=profile, text=x[:220]) for x in lines])
                messages.success(request, "Fun facts saved.")
                return redirect("settings_personal", step=5)
        else:
            existing = ", ".join(profile.funfacts.values_list("text", flat=True))
            form = FunFactsForm(initial={"funfacts_csv": existing})
        return render(request, "accounts/settings_personal.html", {
            "step": step, "steps": PERSONAL_STEPS, "form": form,
        })

    # Step 5: Social links (formset)
    # views.py – Personal step 5
    if step == 5:
        if request.method == "POST":
            fs = SocialLinkFormSet(request.POST, instance=profile)
            if 'skip' in request.POST or fs.is_valid():
                if fs.is_valid():
                    fs.save()
                    messages.success(request, "Social links saved.")
                else:
                    messages.info(request, "Skipped social links for now.")
                return redirect("settings_personal", step=6)
        else:
            fs = SocialLinkFormSet(instance=profile)
        return render(request, "accounts/settings_personal.html", {
            "step": step, "steps": PERSONAL_STEPS, "formset": fs,
        })


    # Step 6: Review
    return render(request, "accounts/settings_personal.html", {
        "step": step, "steps": PERSONAL_STEPS,
        "profile": profile,
    })

# ---------- Portfolio wizard (6 steps) ----------
PORTFOLIO_STEPS = [
    "Education", "Experience", "Projects", "Certs & Courses", "Awards & Books", "Review",
]

@login_required
@transaction.atomic
def settings_portfolio_wizard(request, step=1):
    step = int(step or 1)
    profile = get_object_or_404(Profile, user=request.user)

    def render_step(ctx):
        ctx.update({"step": step, "steps": PORTFOLIO_STEPS})
        return render(request, "accounts/settings_portfolio.html", ctx)

    if step == 1:
        fs = EducationFS(request.POST or None, instance=profile, prefix="edu")
        if request.method == "POST" and fs.is_valid():
            fs.save()
            messages.success(request, "Education updated.")
            return redirect("settings_portfolio", step=2)
        return render_step({"formset": fs})

    if step == 2:
        fs = ExperienceFS(request.POST or None, instance=profile, prefix="exp")
        if request.method == "POST" and fs.is_valid():
            fs.save()
            messages.success(request, "Experience updated.")
            return redirect("settings_portfolio", step=3)
        return render_step({"formset": fs})

    if step == 3:
        fs = ProjectFS(request.POST or None, instance=profile, prefix="proj")
        if request.method == "POST" and fs.is_valid():
            fs.save()
            messages.success(request, "Projects updated.")
            return redirect("settings_portfolio", step=4)
        return render_step({"formset": fs})

    if step == 4:
        certs = CertificationFS(request.POST or None, instance=profile, prefix="cert")
        courses = CourseFS(request.POST or None, instance=profile, prefix="course")
        if request.method == "POST" and certs.is_valid() and courses.is_valid():
            certs.save(); courses.save()
            messages.success(request, "Certifications & Courses saved.")
            return redirect("settings_portfolio", step=5)
        return render_step({"formset_certs": certs, "formset_courses": courses})

    if step == 5:
        awards = AwardFS(request.POST or None, instance=profile, prefix="award")
        books  = BookFS(request.POST or None, instance=profile, prefix="book")
        if request.method == "POST" and awards.is_valid() and books.is_valid():
            awards.save(); books.save()
            messages.success(request, "Awards & Books saved.")
            return redirect("settings_portfolio", step=6)
        return render_step({"formset_awards": awards, "formset_books": books})

    # Step 6 Review
    return render_step({"profile": profile})





from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import redirect
from django.urls import translate_url

@require_POST
@login_required
def set_user_language(request):
    lang = request.POST.get("language") in ("fa", "en") and request.POST["language"] or None
    next_url = request.POST.get("next") or "/"
    if not lang:
        return redirect(next_url)

    request.user.language = lang
    request.user.save(update_fields=["language"])

    # let middleware also sync session, but we redirect now to correct URL
    return redirect(translate_url(next_url, lang))

from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@require_POST
@login_required
def api_save_language(request):
    lang = request.POST.get("language")
    if lang in ("fa","en"):
        request.user.language = lang
        request.user.save(update_fields=["language"])
    return HttpResponse(status=204)

