# core/context_processors.py
from django.db.models import Count
from marketplace.models import ArtPost

def sidebar_top_artposts(request):
    top_n = 8
    posts = (
        ArtPost.objects
        .filter(is_active=True, profile__user__is_active=True)
        .annotate(num_likes=Count("likes"))
        .order_by("-num_likes", "-views", "-updated_at")[:top_n]
    )
    return {"sidebar_top_artposts": posts}
