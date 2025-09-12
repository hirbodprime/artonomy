# suggest/explore_pins.py
from datetime import timedelta
import random
from django.db import transaction
from django.db.models import Count, Q, Max, IntegerField, Value
from django.utils import timezone
from .models import ExplorePin
from posts.models import Post
from core.query import _common_selects  # your helper

LOOKBACK_DAYS_TO_AVOID_REPEAT = 7
SUGGESTS_WINDOW_DAYS = 30
PINS_PER_DAY = 4
POOL_MULTIPLIER = 8

def _base_queryset():
    return _common_selects(Post.objects.all())

def _pick_diverse_by_author(cands, needed):
    picked, seen = [], set()
    for p in cands:
        author_id = getattr(p, "author_id", None)
        k = author_id or f"NOAUTHOR-{p.id}"
        if k in seen:
            continue
        picked.append(p)
        seen.add(k)
        if len(picked) >= needed:
            break
    return picked

def select_today_pins(dry_run=False):
    today = timezone.localdate()

    existing = list(ExplorePin.objects.filter(date=today).select_related("post"))
    if len(existing) >= PINS_PER_DAY:
        return [p.post for p in existing[:PINS_PER_DAY]]

    since_date = today - timedelta(days=LOOKBACK_DAYS_TO_AVOID_REPEAT)
    exclude_recent_ids = ExplorePin.objects.filter(date__gte=since_date).values_list("post_id", flat=True)

    suggests_since = timezone.now() - timedelta(days=SUGGESTS_WINDOW_DAYS)

    qs = (
        _base_queryset()
        .exclude(id__in=exclude_recent_ids)
        .annotate(
            suggests_30=Count(
                "suggestions",
                filter=Q(suggestions__created_at__gte=suggests_since),
                distinct=True,
            ),
            # ✅ use the correct reverse name: explore_pins
            last_pinned=Max("explore_pins__date"),
            pins_total=Count("explore_pins", distinct=True),
            recency_boost=Value(1, output_field=IntegerField()),
        )
        .order_by("-suggests_30", "pins_total", "-created_at")
    )

    pool = list(qs[: PINS_PER_DAY * POOL_MULTIPLIER])
    random.shuffle(pool)

    candidates = _pick_diverse_by_author(pool, PINS_PER_DAY)
    if len(candidates) < PINS_PER_DAY:
        seen_ids = {p.id for p in candidates}
        for p in pool:
            if p.id in seen_ids:
                continue
            candidates.append(p)
            seen_ids.add(p.id)
            if len(candidates) >= PINS_PER_DAY:
                break

    if not dry_run and candidates:
        with transaction.atomic():
            already = ExplorePin.objects.filter(date=today).count()
            still_needed = max(0, PINS_PER_DAY - already)
            to_insert = candidates[:still_needed]
            ExplorePin.objects.bulk_create(
                [ExplorePin(date=today, post=p) for p in to_insert],
                ignore_conflicts=True,
            )

    return candidates
