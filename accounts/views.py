# accounts/views.py
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .onboarding import next_onboarding_step, ROLE_STEP, CATEGORIES_STEP, DONE
from django.contrib.auth import get_user_model
from posts.models import Post
from network.models import Follow
from accounts.models import (
    Profile, Education, Experience, Book, Certification, Course, Project, Award,
    SkillTag, SocialLink, PersonalValue, HobbyInterest, Achievement, Goal, FunFact,UserCategory,Category,User
)
from suggest.models import Suggestion

from django.contrib.auth import logout
from django.urls import reverse

# accounts/views.py  (additions)
from django.contrib import messages
from django.db import transaction
from .forms import (
    ProfileBasicsForm, SkillsCSVForm, ValuesHobbiesForm, FunFactsForm,
    SocialLinkFormSet,
    EducationFS, ExperienceFS, ProjectFS, CertificationFS, CourseFS, AwardFS, BookFS
)

User = get_user_model()



def logout_view(request):
    """Logs out the user and redirects to explore (or login)."""
    logout(request)
    return redirect(reverse("landing"))

def signup_view(request):
    # if request.user:
    #     return redirect('explore')
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")

        if password != password2:
            messages.error(request, "Passwords do not match")
            return render(request, "accounts/signup.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already in use")
            return render(request, "accounts/signup.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return render(request, "accounts/signup.html")

        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        login(request, user)
        # Middleware will redirect correctly, but we can jump straight to role
        return redirect("choose_role")

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
    rel_kind = (
        UserCategory.Kind.WORK if user.role == User.Role.ARTIST else UserCategory.Kind.FAV
    )

    if request.method == "POST":
        slugs = [s.strip() for s in request.POST.get("selected_slugs", "").split(",") if s.strip()]
        cats = list(Category.objects.filter(slug__in=slugs))

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

        messages.success(request, "Preferences saved.")
        return redirect("explore")  # onboarding complete

    chosen_ids = set(
        UserCategory.objects.filter(user=user, kind=rel_kind).values_list("category_id", flat=True)
    )
    categories = Category.objects.all().order_by("name")
    heading_text = "Your Favorite Categories" if rel_kind == UserCategory.Kind.FAV else "Your Work Categories"

    return render(request, "accounts/categories.html", {
    "categories": categories,
    "chosen_ids": chosen_ids,
    "rel_kind": rel_kind,
    "heading_text": heading_text,  # <-- add
})







def profile_view(request, username: str):
    UserModel = get_user_model()
    profile_user = get_object_or_404(
        UserModel.objects.select_related("profile"),
        username=username
    )
    profile = getattr(profile_user, "profile", None)

    # Ensure a profile exists (if you create it in signals, this is a no-op)
    if not hasattr(profile_user, "profile"):
        profile = Profile.objects.create(user=profile_user)
    else:
        profile = profile_user.profile

    # --- follow stats / state ---
    followers_count = profile_user.follower_relations.count()      # users who follow profile_user
    following_count = profile_user.following_relations.count()     # users profile_user follows
    is_following = (
        request.user.is_authenticated
        and request.user != profile_user
        and Follow.objects.filter(follower=request.user, following=profile_user).exists()
    )

    # --- timeline posts (fast prefetch) ---
    timeline_posts = (
        Post.objects
        .filter(author=profile_user)
        .select_related("author", "author__profile")
        .prefetch_related("images", "videos", "chapters")
        .order_by("-created_at")
    )

    # --- personal info blocks ---
    social_links = profile.social_links.all()
    values       = profile.values.all()
    hobbies      = profile.hobbies.all()
    achievements = profile.achievements.all()
    goals        = profile.goals.all()
    funfacts     = profile.funfacts.all()

    # --- portfolio (resume) blocks ---
    educations      = profile.educations.all()
    experiences     = profile.experiences.all()
    skills          = profile.skills.all()
    books           = profile.books.all()
    certifications  = profile.certifications.all()
    courses         = profile.courses.all()
    projects        = profile.projects.all()
    awards          = profile.awards.all()

    # --- marketplace (optional app) ---
    market_items = []
    try:
        # IMPORTANT: use your marketplace app + model names
        from marketplace.models import MarketItem
        market_items = (
            MarketItem.objects
            .filter(seller=profile_user, status=MarketItem.Status.ACTIVE)
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

    # Posts this profile_user has suggested (for later UI)
    suggested_posts = (
        Post.objects
        .filter(suggestions__suggester=profile_user)
        .select_related("author", "author__profile")
        .prefetch_related("images", "videos", "chapters")
        .order_by("-suggestions__created_at")
    )
    if profile_user.role == User.Role.ARTIST:
        kind = UserCategory.Kind.WORK
        hero_cats_label = "Working categories"
    else:
        kind = UserCategory.Kind.FAV
        hero_cats_label = "Favorite categories"

    hero_cats = (
        Category.objects
        .filter(usercategory__user=profile_user, usercategory__kind=kind)
        .order_by("name")[:6]   # show up to 6 chips
    )
    show_market = (profile_user.role == User.Role.ARTIST)

    is_owner = request.user.is_authenticated and request.user == profile_user
    ctx = {
        "nav_active": None,
        "profile_user": profile_user,
        "profile": profile,
        "show_market": show_market,

        # follow info
        "followers_count": followers_count,
        "following_count": following_count,
        "is_following_author": is_following,

        # timeline
        "timeline_posts": timeline_posts,
        "is_owner": is_owner,
        # personal info
        "social_links": social_links,
        "values": values,
        "hobbies": hobbies,
        "achievements": achievements,
        "goals": goals,
        "funfacts": funfacts,

        # portfolio (resume)
        "educations": educations,
        "experiences": experiences,
        "skills": skills,
        "books": books,
        "certifications": certifications,
        "courses": courses,
        "projects": projects,
        "awards": awards,

        # marketplace
        "market_items": market_items,

        "profile_user": profile_user,
        "profile": profile,
        "hero_cats": hero_cats,
        "hero_cats_label": hero_cats_label,
        "suggestions_made_count": suggestions_made_count,
        "suggestions_received_count": suggestions_received_count,
        "suggested_posts": suggested_posts,

    }
    return render(request, "accounts/profile.html", ctx)




















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
