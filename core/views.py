from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect,get_object_or_404

from django.contrib.auth import get_user_model
from datetime import timedelta
from django.db.models import (F, Q, Value, IntegerField, FloatField, Count, Case, When,ExpressionWrapper)
from django.db.models.functions import Now, Coalesce
from network.models import Follow
from accounts.models import UserCategory  # your through model
from posts.models import Post, Category, Like  # your posts app

User = get_user_model()


def _cat_filter(queryset, active_category):
    """Apply category filter if present."""
    if active_category:
        queryset = queryset.filter(categories=active_category)
    return queryset


def _common_selects(qs):
    """Shared select_related/prefetch for cards & single view parity."""
    return (
        qs.select_related("author")
          .prefetch_related("images", "videos", "chapters", "categories")
    )


def home_view(request):
    """
    Home: ONLY posts from authors the user follows + the user's own posts,
    ordered by newest first. Anonymous users see nothing (intentional).
    Optional filter: ?cat=<slug>
    """
    cat_slug = request.GET.get("cat")
    categories = Category.objects.all().order_by("name")
    active_category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

    if request.user.is_authenticated:
        following_ids = Follow.objects.filter(
            follower=request.user
        ).values_list("following_id", flat=True)

        qs = Post.objects.filter(
            Q(author_id__in=following_ids) | Q(author=request.user)
        ).order_by("-created_at")

        qs = _cat_filter(qs, active_category)
        qs = _common_selects(qs)
    else:
        # You asked for "only following + own" — so anonymous gets an empty feed
        qs = Post.objects.none()

    context = {
        "nav_active": "home",
        "categories": categories,
        "active_category": active_category,
        "posts": qs,
    }
    return render(request, "home.html", context)


# ----- helpers -----
def _common_selects(qs):
    return (qs.select_related("author")
             .prefetch_related("images", "videos", "categories", "chapters"))

def _cat_filter(qs, active_category):
    return qs.filter(categories=active_category) if active_category else qs

def _recency_boost():
    """Tiered recency multiplier: simple & DB-agnostic."""
    return Case(
        When(created_at__gte=Now() - Value(timedelta(days=2)),  then=Value(1.6)),
        When(created_at__gte=Now() - Value(timedelta(days=7)),  then=Value(1.3)),
        When(created_at__gte=Now() - Value(timedelta(days=30)), then=Value(1.1)),
        default=Value(1.0),
        output_field=FloatField(),
    )

def _popularity():
    """3*likes + 2*bookmarks + 2*shares + 1*views with null-safe Coalesce."""
    return (
        3 * Coalesce(F("likes"),     Value(0)) +
        2 * Coalesce(F("bookmarks"), Value(0)) +
        2 * Coalesce(F("shares"),    Value(0)) +
        1 * Coalesce(F("views"),     Value(0))
    )

def _diversify(qs, limit=60, max_per_author=3):
    """
    Greedy author cap. Fetch a buffer, then trim in Python.
    Keeps ordering from the DB.
    """
    buf = list(qs[:200])  # small buffer
    out, per_author = [], {}
    for p in buf:
        a = p.author_id
        if per_author.get(a, 0) >= max_per_author:
            continue
        per_author[a] = per_author.get(a, 0) + 1
        out.append(p)
        if len(out) >= limit:
            break
    return out

# ----- EXPLORE -----
def explore_view(request):
    """
    Explore: two feeds
      - posts_bests: popularity × recency
      - posts_for_you: preference-weighted + popularity × recency (+follow boost)
    Both respect ?cat=<slug>.
    """
    cat_slug = request.GET.get("cat")
    categories = Category.objects.all().order_by("name")
    active_category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

    base = _common_selects(_cat_filter(Post.objects.all(), active_category))

    # ---------- Artonomy Bests ----------
    recency = _recency_boost()
    pop     = _popularity()
    posts_bests_qs = (
        base
        .annotate(pop=pop, recency=recency)
        .annotate(score=F("pop") * F("recency"))
        .order_by("-score", "-created_at")
    )

    # ---------- For You ----------
    posts_for_you_qs = base
    if request.user.is_authenticated:
        # user category preferences
        work_ids = list(
            UserCategory.objects
            .filter(user=request.user, kind=UserCategory.Kind.WORK)
            .values_list("category_id", flat=True)
        )
        fav_ids = list(
            UserCategory.objects
            .filter(user=request.user, kind=UserCategory.Kind.FAV)
            .values_list("category_id", flat=True)
        )
        liked_cat_ids = list(
            Like.objects
            .filter(user=request.user)
            .values_list("post__categories", flat=True)
        )

        # any preferences?
        pref_ids = set([cid for cid in (work_ids + fav_ids + liked_cat_ids) if cid])

        # follow boost (small)
        following_ids = list(
            Follow.objects.filter(follower=request.user)
            .values_list("following_id", flat=True)
        )

        if pref_ids:
            interest_work = Count(
                "categories", filter=Q(categories__in=work_ids), distinct=True
            ) * Value(3, output_field=IntegerField())
            interest_fav = Count(
                "categories", filter=Q(categories__in=fav_ids), distinct=True
            ) * Value(2, output_field=IntegerField())
            interest_like = Count(
                "categories", filter=Q(categories__in=liked_cat_ids), distinct=True
            ) * Value(1, output_field=IntegerField())

            follow_bonus = Case(
                When(author_id__in=following_ids, then=Value(5)),
                default=Value(0),
                output_field=IntegerField(),
            )

            posts_for_you_qs = (
                posts_for_you_qs
                .filter(categories__in=list(pref_ids))
                .distinct()
                .annotate(
                    interest=interest_work + interest_fav + interest_like,
                    pop=pop,
                    recency=recency,
                    follow_bonus=follow_bonus,
                )
                # weight interest higher so it actually changes order
                .annotate(score=F("interest") * Value(10) + F("pop") * F("recency") + F("follow_bonus"))
                .order_by("-score", "-created_at")
            )
        else:
            # cold start → same as bests
            posts_for_you_qs = posts_bests_qs
    else:
        posts_for_you_qs = posts_bests_qs  # anon → same as bests

    # diversity (cap per author), and limit what you render for speed
    posts_bests = _diversify(posts_bests_qs, limit=60, max_per_author=3)
    posts_for_you = _diversify(posts_for_you_qs, limit=60, max_per_author=3)

    return render(request, "explore.html", {
        "nav_active": "explore",
        "categories": categories,
        "active_category": active_category,
        "posts_bests": posts_bests,
        "posts_for_you": posts_for_you,
        # default feed tab = 'bests' unless user passed ?feed=for-you
        "feed_tab": request.GET.get("feed", "bests"),
    })

def landing_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        print(" Login attempt on landing_page")
        print("Email entered:", email)
        print("Password length:", len(password) if password else 0)

        user = authenticate(request, email=email, password=password)
        print("Authenticate returned:", user)

        if user is not None:
            login(request, user)
            print("Login successful for:", user)
            return redirect("explore")   # or wherever your post-login page is
        else:
            print("Invalid login credentials")
            messages.error(request, "Invalid email or password")

    return render(request, "landing_page.html")











def coming_soon_view(req):
    return render(req,'coming_soon.html')