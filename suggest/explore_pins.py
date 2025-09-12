# app/services/explore_pins.py
from datetime import timedelta
import random
from django.db import transaction
from django.db.models import Count, Q, Max, IntegerField, Value
from django.utils import timezone
from .models import ExplorePin
from posts.models import Post
from core.query import _common_selects  # keep your helper

# Tune these
LOOKBACK_DAYS_TO_AVOID_REPEAT = 7    # ← avoid repeating within the last week
SUGGESTS_WINDOW_DAYS = 30
PINS_PER_DAY = 4
POOL_MULTIPLIER = 8                  # build a pool of N*8, then randomize

def _base_queryset():
    return _common_selects(Post.objects.all())

def _pick_diverse_by_author(candidates, needed):
    """Pick up to `needed` posts ensuring author diversity (max 1 per author)."""
    picked, seen_authors = [], set()
    for p in candidates:
        author_id = getattr(p, "author_id", None) or getattr(p, "user_id", None) or getattr(p, "owner_id", None)
        # Fall back to object id if you don’t have an author FK
        author_key = author_id or f"NOAUTHOR-{p.id}"
        if author_key in seen_authors:
            continue
        picked.append(p)
        seen_authors.add(author_key)
        if len(picked) >= needed:
            break
    return picked

def select_today_pins(dry_run=False):
    today = timezone.localdate()

    # Already pinned today? return them (idempotent restarts)
    existing = list(ExplorePin.objects.filter(date=today).select_related('post'))
    if len(existing) >= PINS_PER_DAY:
        return [p.post for p in existing[:PINS_PER_DAY]]

    # Exclude anything pinned within lookback window
    since_date = today - timedelta(days=LOOKBACK_DAYS_TO_AVOID_REPEAT)
    exclude_recent_ids = ExplorePin.objects.filter(date__gte=since_date).values_list("post_id", flat=True)

    # Compute “recent suggests” window
    suggests_since = timezone.now() - timedelta(days=SUGGESTS_WINDOW_DAYS)

    # Annotate with last_pinned and total pins to break ties away from over-exposed posts
    qs = (
        _base_queryset()
        .exclude(id__in=exclude_recent_ids)
        .annotate(
            suggests_30=Count(
                "suggestions",
                filter=Q(suggestions__created_at__gte=suggests_since),
                distinct=True,
            ),
            last_pinned=Max("explorepin__date"),
            pins_total=Count("explorepin", distinct=True),
            recency_boost=Value(1, output_field=IntegerField()),
        )
        # Prefer higher suggests; then least pinned; then newer content
        .order_by("-suggests_30", "pins_total", "-created_at")
    )

    # Build a pool bigger than needed, then randomize in Python
    pool_size = PINS_PER_DAY * POOL_MULTIPLIER
    pool = list(qs[:pool_size])

    # Shuffle to avoid deterministic tops
    random.shuffle(pool)

    # Enforce author diversity
    candidates = _pick_diverse_by_author(pool, PINS_PER_DAY)

    # If we still don't have enough (e.g., few authors), fill from the remaining pool
    if len(candidates) < PINS_PER_DAY:
        # allow duplicates by author only if we must
        seen_ids = {p.id for p in candidates}
        for p in pool:
            if p.id in seen_ids:
                continue
            candidates.append(p)
            seen_ids.add(p.id)
            if len(candidates) >= PINS_PER_DAY:
                break

    # Persist
    if not dry_run and candidates:
        with transaction.atomic():
            # Re-check how many are missing inside tx
            already = ExplorePin.objects.filter(date=today).count()
            still_needed = max(0, PINS_PER_DAY - already)
            to_insert = candidates[:still_needed]
            ExplorePin.objects.bulk_create(
                [ExplorePin(date=today, post=p) for p in to_insert],
                ignore_conflicts=True,
            )

    return candidates
