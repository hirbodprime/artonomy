# app/services/explore_pins.py
from datetime import timedelta
from django.db import transaction
from django.db.models import Count, Q, F, Value, IntegerField
from django.utils import timezone
from .models import ExplorePin
from posts.models import Post  # adjust import to your project
from core.query import _common_selects
# If you keep helpers in the same file, import accordingly.

LOOKBACK_DAYS_TO_AVOID_REPEAT = 1          # don't repeat from yesterday
SUGGESTS_WINDOW_DAYS = 30                  # “recent” suggestions window
PINS_PER_DAY = 4

def _base_queryset():
    # Mirror your explore base qs (no cat filter here; global pins)
    return _common_selects(Post.objects.all())

def select_today_pins(dry_run=False):
    today = timezone.localdate()

    # Already pinned today?
    existing = list(ExplorePin.objects.filter(date=today).select_related('post'))
    if len(existing) >= PINS_PER_DAY:
        return [p.post for p in existing[:PINS_PER_DAY]]

    # Exclude posts that were pinned in the lookback window
    since = today - timedelta(days=LOOKBACK_DAYS_TO_AVOID_REPEAT)
    exclude_ids = ExplorePin.objects.filter(date__gte=since).values_list('post_id', flat=True)

    # Count recent suggests; break ties with recency + created_at
    suggests_since = timezone.now() - timedelta(days=SUGGESTS_WINDOW_DAYS)
    qs = (
        _base_queryset()
        .exclude(id__in=exclude_ids)
        .annotate(
            suggests_30=Count(
                'suggestions',
                filter=Q(suggestions__created_at__gte=suggests_since),
                distinct=True,
            ),
            # small recency multiplier to break ties in favor of newer/popular
            recency_boost=Value(1, output_field=IntegerField())
        )
        .order_by('-suggests_30', '-created_at')
    )

    candidates = list(qs[:PINS_PER_DAY])

    if not dry_run:
        with transaction.atomic():
            # Re-check inside transaction (avoid race)
            still_missing = PINS_PER_DAY - ExplorePin.objects.filter(date=today).count()
            to_insert = candidates[:max(0, still_missing)]
            ExplorePin.objects.bulk_create([ExplorePin(date=today, post=p) for p in to_insert], ignore_conflicts=True)

    return candidates
