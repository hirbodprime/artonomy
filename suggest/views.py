# suggest/views.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from django.contrib.auth import get_user_model
from posts.models import Post
from .models import Suggestion

User = get_user_model()


@login_required
@require_POST
def toggle_suggestion(request, post_id: int):
    """
    Toggle suggestion on a post by the current user.
    Returns JSON with current status + a few handy counts.
    """
    post = get_object_or_404(Post.objects.select_related("author"), pk=post_id)
    if post.author_id == request.user.id:
        return JsonResponse({"ok": False, "error": "You cannot suggest your own post."}, status=400)

    obj, created = Suggestion.objects.get_or_create(
        suggester=request.user,
        post=post,
        defaults={"note": request.POST.get("note", "").strip()[:500]},
    )
    if created:
        suggested = True
    else:
        obj.delete()
        suggested = False

    # Some useful counts to update UI if needed
    post_suggestions = Suggestion.objects.filter(post=post).count()
    author_received = Suggestion.objects.filter(post__author=post.author).count()
    user_made = Suggestion.objects.filter(suggester=request.user).count()

    return JsonResponse({
        "ok": True,
        "suggested": suggested,
        "counts": {
            "post": post_suggestions,
            "author_received": author_received,
            "user_made": user_made,
        }
    })


# -------- Optional simple list pages (no styling; you can hook to any template later) --------

def list_suggested_by_user(request, username: str):
    user = get_object_or_404(User, username=username)
    qs = (Suggestion.objects
          .filter(suggester=user)
          .select_related("post", "post__author", "post__author__profile")
          .order_by("-created_at"))
    return render(request, "suggest/by_user.html", {"owner": user, "suggestions": qs})


def list_suggesters_for_post(request, post_id: int):
    post = get_object_or_404(Post.objects.select_related("author", "author__profile"), pk=post_id)
    qs = (Suggestion.objects
          .filter(post=post)
          .select_related("suggester", "suggester__profile")
          .order_by("-created_at"))
    return render(request, "suggest/for_post.html", {"post": post, "suggestions": qs})
