# views.py

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.template.loader import render_to_string

from django.db.models import Q
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone

from network.models import Follow
from accounts.models import UserCategory  # through model
from posts.models import Post, Category
from suggest.models import ExplorePin
from suggest.explore_pins import select_today_pins  # if you use self-heal

User = get_user_model()

# =========================
# Tuning knobs for feeds
# =========================
PAGE_SIZE = 24          # items per page (initial and API pages)
BUFFER = 500            # how many IDs we consider before slicing to a page
PER_AUTHOR_CAP = 0      # 0 = no per-author cap in page chunks (safer for "all posts")


# ========= Shared lightweight helpers =========

def _light_base():
    """Minimal selection for fast lists (no heavy prefetch)."""
    return Post.objects.select_related("author")

def _apply_category(qs, active_category):
    """
    Optional category filter. Use distinct() ONLY when category is active
    to avoid duplicate rows from M2M join consuming page slots.
    """
    if active_category:
        return qs.filter(categories=active_category).distinct()
    return qs

def _cap_per_author(posts, limit, cap):
    """
    Greedy per-author cap. If cap == 0, return the input (no cap).
    Use ONLY on page-sized chunks; applying globally starves later pages.
    """
    if not cap:
        return list(posts)[:limit]
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

def _dedup_ordered(ids):
    """De-duplicate while preserving order (sqlite-friendly)."""
    seen, out = set(), []
    for x in ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ========= HOME (simplified & SQLite-friendly) =========

def home_view(request):
    """
    Home: ONLY posts from authors the user follows + the user's own posts,
    newest first. Optional filter: ?cat=<slug>. Returns the first PAGE_SIZE;
    the rest are loaded via /home/feed API by your JS.
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

        base = _light_base().filter(Q(author_id__in=following_ids) | Q(author=request.user))
        qs = _apply_category(base, active_category).order_by("-created_at", "-id")

    # first page only; infinite scroll calls /home/feed for the next ones
    posts_page = list(qs[:PAGE_SIZE])

    context = {
        "nav_active": "home",
        "categories": categories,
        "active_category": active_category,
        "posts": posts_page,
        "page": 1,
        "has_next": len(posts_page) == PAGE_SIZE,
    }
    return render(request, "home.html", context)


# ========= EXPLORE (MVP-fast, SQLite-friendly) =========

def _explore_id_lists(request, active_category):
    """
    Build ID lists for 'bests' and 'for_you' (deduped, ordered) without heavy SQL.
    """
    # ---------- Artonomy Bests (cheap) ----------
    bests_qs = _apply_category(_light_base(), active_category).order_by("-likes", "-created_at", "-id")
    best_ids = list(bests_qs.values_list("id", flat=True)[:BUFFER])
    best_ids = _dedup_ordered(best_ids)

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

        # merge and de-dup in Python
        merged = []
        seen = set()
        for it in q_id_iters:
            for pid in it:
                if pid not in seen:
                    seen.add(pid)
                    merged.append(pid)
        for_you_ids = _dedup_ordered(merged)[:BUFFER]

    # Fallback (anon / no prefs) → use bests ordering
    if not for_you_ids:
        for_you_ids = list(best_ids)

    return best_ids, for_you_ids


def explore_view(request):
    """
    Explore landing: serve the FIRST PAGE for both feeds.
    Infinite scroll uses /explore/feed API for further pages.
    """
    cat_slug = request.GET.get("cat")
    categories = Category.objects.all().order_by("name")
    active_category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

    best_ids, for_you_ids = _explore_id_lists(request, active_category)

    # fetch first PAGE_SIZE for each feed (sort in Python for stability)
    def fetch_first(ids):
        items = list(_light_base().filter(id__in=ids))
        items.sort(key=lambda p: (p.created_at, p.likes, p.id), reverse=True)
        return items[:PAGE_SIZE], len(items) > PAGE_SIZE

    best_posts, best_has_more = fetch_first(best_ids)
    for_you_posts, fy_has_more = fetch_first(for_you_ids)

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
        "page": 1,
        "has_next_bests": best_has_more,
        "has_next_for_you": fy_has_more,
    })


# ========= Auth / Landing (unchanged) =========

@ensure_csrf_cookie
def landing_page(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect("explore")
        else:
            messages.error(request, "Invalid email or password")

    return render(request, "landing_page.html")


def coming_soon_view(req):
    return render(req, 'coming_soon.html')


# ========= JSON APIs for infinite scroll =========

def home_feed_api(request):
    """
    GET params: page=2.., cat=<slug>
    Returns: html_mobile, html_desktop, has_next
    """
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


def explore_feed_api(request):
    """
    GET params: feed=bests|for-you, page=1.., cat=<slug>
    Returns: html chunks + has_next for infinite scroll.
    """
    feed = (request.GET.get("feed") or "bests").lower()
    try:
        page = max(int(request.GET.get("page", 1)), 1)
    except ValueError:
        page = 1

    cat_slug = request.GET.get("cat")
    active_category = Category.objects.filter(slug=cat_slug).first() if cat_slug else None

    best_ids, for_you_ids = _explore_id_lists(request, active_category)
    ids = for_you_ids if feed == "for-you" else best_ids

    # fetch all candidates, apply global order once
    items = list(_light_base().filter(id__in=ids))
    items.sort(key=lambda p: (p.created_at, p.likes, p.id), reverse=True)

    # paginate FIRST, then (optionally) cap per author within the page
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_chunk = items[start:end]

    # if you want diversity inside the page, set PER_AUTHOR_CAP > 0
    posts = _cap_per_author(page_chunk, limit=PAGE_SIZE, cap=PER_AUTHOR_CAP)
    has_next = len(page_chunk) == PAGE_SIZE

    html_mobile  = render_to_string("partials/explore_cards_mobile.html",  {"posts": posts}, request=request)
    html_desktop = render_to_string("partials/explore_cards_desktop.html", {"posts": posts}, request=request)
    return JsonResponse({"html_mobile": html_mobile, "html_desktop": html_desktop, "has_next": has_next})
