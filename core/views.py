from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model

from django.db.models import Q
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone

from network.models import Follow
from accounts.models import UserCategory  # through model
from posts.models import Post, Category
from suggest.models import ExplorePin
from suggest.explore_pins import select_today_pins  # if you use self-heal

User = get_user_model()

# ---- Tuning knobs for lightweight feeds ----
PAGE_SIZE = 5          # how many items we show
BUFFER = 200            # how many IDs to pull before trimming
PER_AUTHOR_CAP = 3      # diversity cap per author


# ========= Shared lightweight helpers =========

def _light_base():
    """Minimal selection for fast lists (no heavy prefetch)."""
    return Post.objects.select_related("author")

def _apply_category(qs, active_category):
    """Optional category filter by instance."""
    return qs.filter(categories=active_category) if active_category else qs

def _cap_per_author(posts, limit=PAGE_SIZE, cap=PER_AUTHOR_CAP):
    """Greedy per-author cap done in Python (cheap on small buffers)."""
    out, seen_per_author = [], {}
    for p in posts:
        a = p.author_id
        if seen_per_author.get(a, 0) >= cap:
            continue
        seen_per_author[a] = seen_per_author.get(a, 0) + 1
        out.append(p)
        if len(out) >= limit:
            break
    return out


# ========= HOME (simplified & SQLite-friendly) =========

def home_view(request):
    """
    Home: ONLY posts from authors the user follows + the user's own posts,
    newest first. Optional filter: ?cat=<slug>. Minimal selects + early limit.
    """
    cat_slug = request.GET.get("cat")
    categories = Category.objects.all().order_by("name")
    active_category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

    if not request.user.is_authenticated:
        qs = Post.objects.none()
    else:
        following_ids = Follow.objects.filter(
            follower=request.user
        ).values_list("following_id", flat=True)

        base = _light_base().filter(
            Q(author_id__in=following_ids) | Q(author=request.user)
        )
        qs = _apply_category(base, active_category).order_by("-created_at", "-id")

    # Simple offset pagination (keeps template changes minimal)
    # If you don’t want pagination yet, comment the slice and pass qs directly.
    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        page = 1
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    posts_page = list(qs[start:end])

    context = {
        "nav_active": "home",
        "categories": categories,
        "active_category": active_category,
        "posts": posts_page,
        "page": page,
        "has_next": len(posts_page) == PAGE_SIZE,  # simple next flag
    }
    return render(request, "home.html", context)


# ========= EXPLORE (MVP-fast, SQLite-friendly) =========

def explore_view(request):
    """
    Explore: two feeds (cheap)
      - posts_bests: order by -likes, then -created_at
      - posts_for_you: union of followed authors + WORK/FAV categories, newest first
    Both respect ?cat=<slug>. De-dup + author cap in Python.
    """
    cat_slug = request.GET.get("cat")
    categories = Category.objects.all().order_by("name")
    active_category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

    # ---------- Artonomy Bests (cheap) ----------
    bests_qs = _apply_category(_light_base(), active_category).order_by("-likes", "-created_at", "-id")
    best_ids = list(bests_qs.values_list("id", flat=True)[:BUFFER])

    # ---------- For You (cheap union) ----------
    for_you_ids = []
    if request.user.is_authenticated:
        following_ids = list(
            Follow.objects.filter(follower=request.user)
            .values_list("following_id", flat=True)
        )
        work_ids = list(
            UserCategory.objects.filter(user=request.user, kind=UserCategory.Kind.WORK)
            .values_list("category_id", flat=True)
        )
        fav_ids = list(
            UserCategory.objects.filter(user=request.user, kind=UserCategory.Kind.FAV)
            .values_list("category_id", flat=True)
        )
        pref_cat_ids = list(set(work_ids + fav_ids))

        base = _apply_category(_light_base(), active_category)

        q_id_iters = []
        if following_ids:
            q_id_iters.append(
                base.filter(author_id__in=following_ids)
                    .order_by("-created_at", "-id")
                    .values_list("id", flat=True)[:BUFFER]
            )
        if pref_cat_ids:
            q_id_iters.append(
                base.filter(categories__in=pref_cat_ids)
                    .order_by("-created_at", "-id")
                    .values_list("id", flat=True)[:BUFFER]
            )

        # merge ids in Python (avoid DISTINCT on sqlite)
        seen = set()
        merged = []
        for it in q_id_iters:
            for pid in it:
                if pid not in seen:
                    seen.add(pid)
                    merged.append(pid)
        for_you_ids = merged[:BUFFER]

    # Fallback for anon / no prefs
    if not for_you_ids:
        for_you_ids = best_ids[:BUFFER]

    # ---------- Fetch & order in Python ----------
    best_posts = list(_light_base().filter(id__in=best_ids))
    for_you_posts = list(_light_base().filter(id__in=for_you_ids))

    best_posts.sort(key=lambda p: (p.created_at, p.likes, p.id), reverse=True)
    for_you_posts.sort(key=lambda p: (p.created_at, p.likes, p.id), reverse=True)

    # diversity + final limit
    best_posts = _cap_per_author(best_posts, limit=PAGE_SIZE, cap=PER_AUTHOR_CAP)
    for_you_posts = _cap_per_author(for_you_posts, limit=PAGE_SIZE, cap=PER_AUTHOR_CAP)

    # (optional) pins — keep or skip if slow
    today = timezone.localdate()
    pin_qs = ExplorePin.objects.filter(date=today).select_related('post')
    pinned_posts = [p.post for p in pin_qs.order_by('created_at')[:4]]

    return render(request, "explore.html", {
        "nav_active": "explore",
        "categories": categories,
        "active_category": active_category,
        "posts_bests": best_posts,
        "posts_for_you": for_you_posts,
        "pinned_posts": pinned_posts,
        "feed_tab": request.GET.get("feed", "bests"),
    })


# ========= Auth / Landing (unchanged) =========

@ensure_csrf_cookie
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
    return render(req, 'coming_soon.html')



# views.py  (add imports at top)
from django.http import JsonResponse
from django.template.loader import render_to_string

# HOME API
def home_feed_api(request):
    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        page = 1

    cat_slug = request.GET.get("cat")
    active_category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

    if not request.user.is_authenticated:
        return JsonResponse({"html_mobile": "", "html_desktop": "", "has_next": False})

    following_ids = Follow.objects.filter(
        follower=request.user
    ).values_list("following_id", flat=True)

    base = _light_base().filter(Q(author_id__in=following_ids) | Q(author=request.user))
    qs = _apply_category(base, active_category).order_by("-created_at", "-id")

    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    posts = list(qs[start:end])
    has_next = len(posts) == PAGE_SIZE

    html_mobile  = render_to_string("partials/home_cards_mobile.html",  {"posts": posts}, request=request)
    html_desktop = render_to_string("partials/home_cards_desktop.html", {"posts": posts}, request=request)
    return JsonResponse({"html_mobile": html_mobile, "html_desktop": html_desktop, "has_next": has_next})


# EXPLORE API
def explore_feed_api(request):
    """
    expects: feed=bests|for-you, page=1.., cat=<slug>
    returns: html chunks for current viewport (we return both; JS picks which to append)
    """
    feed = (request.GET.get("feed") or "bests").lower()
    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        page = 1

    cat_slug = request.GET.get("cat")
    active_category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

    # --- compute the two lists exactly like your explore_view (fast/MVP) ---
    # Bests
    bests_qs = _apply_category(_light_base(), active_category).order_by("-likes", "-created_at", "-id")
    best_ids = list(bests_qs.values_list("id", flat=True)[:BUFFER])

    # For You
    for_you_ids = []
    if request.user.is_authenticated:
        following_ids = list(
            Follow.objects.filter(follower=request.user)
            .values_list("following_id", flat=True)
        )
        work_ids = list(
            UserCategory.objects.filter(user=request.user, kind=UserCategory.Kind.WORK)
            .values_list("category_id", flat=True)
        )
        fav_ids = list(
            UserCategory.objects.filter(user=request.user, kind=UserCategory.Kind.FAV)
            .values_list("category_id", flat=True)
        )
        pref_cat_ids = list(set(work_ids + fav_ids))

        base = _apply_category(_light_base(), active_category)

        q_id_iters = []
        if following_ids:
            q_id_iters.append(
                base.filter(author_id__in=following_ids)
                    .order_by("-created_at", "-id")
                    .values_list("id", flat=True)[:BUFFER]
            )
        if pref_cat_ids:
            q_id_iters.append(
                base.filter(categories__in=pref_cat_ids)
                    .order_by("-created_at", "-id")
                    .values_list("id", flat=True)[:BUFFER]
            )

        seen, merged = set(), []
        for it in q_id_iters:
            for pid in it:
                if pid not in seen:
                    seen.add(pid)
                    merged.append(pid)
        for_you_ids = merged[:BUFFER]

    if not for_you_ids:
        for_you_ids = best_ids[:BUFFER]

    # fetch + global order (same as page)
    if feed == "for-you":
        items = list(_light_base().filter(id__in=for_you_ids))
    else:
        items = list(_light_base().filter(id__in=best_ids))

    items.sort(key=lambda p: (p.created_at, p.likes, p.id), reverse=True)
    items = _cap_per_author(items, limit=BUFFER, cap=PER_AUTHOR_CAP)

    # paginate the items list
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    posts = items[start:end]
    has_next = len(posts) == PAGE_SIZE

    html_mobile  = render_to_string("partials/explore_cards_mobile.html",  {"posts": posts}, request=request)
    html_desktop = render_to_string("partials/explore_cards_desktop.html", {"posts": posts}, request=request)
    return JsonResponse({"html_mobile": html_mobile, "html_desktop": html_desktop, "has_next": has_next})
