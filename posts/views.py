from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse, HttpResponseBadRequest
from network.models import Follow
from .models import (Post, Like, Bookmark, Comment, TextChapter, Category, Tool, Inspiration, Tag,)
from django.contrib.auth import get_user_model
from django.http import Http404
from suggest.models import Suggestion
User = get_user_model()

WTYPE = "post_wizard_type"
WPOST = "post_wizard_id"


def _csv_list(s: str):
    if not s:
        return []
    seen, out = set(), []
    for x in [p.strip() for p in s.split(",")]:
        if x and x.lower() not in seen:
            out.append(x)
            seen.add(x.lower())
    return out


def _draft(request, must=True) -> Post | None:
    pid = request.session.get(WPOST)
    if not pid:
        if must:
            raise Http404("No draft in progress.")
        return None
    p = Post.objects.filter(pk=pid, author=request.user).first()
    if not p and must:
        raise Http404("Draft not found.")
    return p


@login_required
def post_new_reset(request):
    p = _draft(request, must=False)
    if p and p.is_draft:
        p.delete()
    request.session.pop(WTYPE, None)
    request.session.pop(WPOST, None)
    return redirect("post_new_start")


@login_required
def post_new_start(request):
    # pure selection screen; anchors carry ?t=PHOTO|VIDEO|TEXT
    return render(request, "posts/upload_select_post_type1.html", {})


@login_required
@transaction.atomic
def post_new_media(request):
    # accept ?t=PHOTO/VIDEO and remember in session
    t = request.GET.get("t") or request.session.get(WTYPE)
    if t not in (Post.PostType.PHOTO, Post.PostType.VIDEO):
        return redirect("post_new_start")
    request.session[WTYPE] = t

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        length = request.POST.get("artwork_length", "").strip()
        tools  = request.POST.get("tools", "")
        tags   = request.POST.get("tags", "")
        inspirations = request.POST.get("inspirations", "")
        caption = request.POST.get("caption", "").strip()
        f = request.FILES.get("file")

        if not title or not f:
            # re-render exactly same page; no design change
            ctx = {"post_type": t, "error": "Please add a title and upload a file."}
            return render(request, "posts/upload_detail_media2.html", ctx)

        p = Post.objects.create(
            author=request.user,
            title=title,
            post_type=t,
            caption=caption,
            artwork_length=length,
            is_draft=True,
        )
        if t == Post.PostType.PHOTO:
            p.image = f
        else:
            p.video = f
        p.save()

        for name in _csv_list(tools):
            obj, _ = Tool.objects.get_or_create(name=name)
            p.tools.add(obj)
        for name in _csv_list(inspirations):
            obj, _ = Inspiration.objects.get_or_create(name=name)
            p.inspirations.add(obj)
        for name in _csv_list(tags):
            obj, _ = Tag.objects.get_or_create(name=name)
            p.tags.add(obj)

        request.session[WPOST] = p.pk
        return redirect("post_new_category")

    return render(request, "posts/upload_detail_media2.html", {"post_type": t})

@login_required
@transaction.atomic
def post_new_text(request):
    t = request.GET.get("t") or request.session.get(WTYPE)
    if t != Post.PostType.TEXT:
        return redirect("post_new_start")
    request.session[WTYPE] = t

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        if not title:
            return render(request, "posts/upload_detail_text2.html", {"error": "Please add a title."})

        p = Post.objects.create(
            author=request.user,
            title=title,
            post_type=Post.PostType.TEXT,
            is_draft=True,
            cover=request.FILES.get("cover")  # ← save cover if provided
        )

        titles = request.POST.getlist("chapter_title[]")
        bodies  = request.POST.getlist("chapter_content[]")

        order = 1
        for ct, cb in zip(titles, bodies):
            ct, cb = (ct or "").strip(), (cb or "").strip()
            if cb:
                TextChapter.objects.create(post=p, order=order, title=ct, content=cb)
                order += 1

        if bodies:
            p.body = (bodies[0] or "").strip()
        p.save()

        request.session[WPOST] = p.pk
        return redirect("post_new_category")

    return render(request, "posts/upload_detail_text2.html", {})


@login_required
def post_new_category(request):
    p = _draft(request)
    categories = Category.objects.all().order_by("name")
    if request.method == "POST":
        ids = request.POST.getlist("categories[]")
        p.categories.set(Category.objects.filter(pk__in=ids))
        p.save()
        return redirect("post_new_review")
    return render(request, "posts/upload_select_category3.html", {"categories": categories, "post": p})


@login_required
@transaction.atomic
def post_new_review(request):
    p = _draft(request)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "publish":
            p.is_draft = False
            p.save()
            request.session.pop(WTYPE, None)
            request.session.pop(WPOST, None)
            return redirect("single_post", pk=p.pk)  # adjust if your name differs
        if action == "draft":
            # keep as draft, clear wizard
            request.session.pop(WTYPE, None)
            request.session.pop(WPOST, None)
            return redirect("profile_view", username=request.user.username)
    return render(request, "posts/upload_review_publish4.html", {"post": p})




# posts/views.py
def _bump_view(pk: int) -> None:
    # atomic increment on every hit
    Post.objects.filter(pk=pk).update(views=F("views") + 1)

# def _bump_view_once(request, pk: int):
#     key = "viewed_posts"
#     viewed = request.session.get(key, [])
#     if pk not in viewed:
#         Post.objects.filter(pk=pk).update(views=F("views") + 1)
#         viewed.append(pk)
#         request.session[key] = viewed

# views.py
from suggest.models import Suggestion  # add
# views.py
from django.db.models import Q

def single_post_view(request, pk):
    post = get_object_or_404(
        Post.objects.select_related("author")
            .prefetch_related("images", "videos", "chapters", "categories", "comments__author"),
        pk=pk
    )

    _bump_view(post.pk)
    post.refresh_from_db(fields=["views"])

    is_liked = is_saved = is_suggested = False
    if request.user.is_authenticated:
        is_liked = Like.objects.filter(user=request.user, post=post).exists()
        is_saved = Bookmark.objects.filter(user=request.user, post=post).exists()
        is_suggested = Suggestion.objects.filter(suggester=request.user, post=post).exists()

    # Next/Prev by pk (simple + fast). Swap to created_at if you prefer chronology.
    next_post = Post.objects.filter(pk__gt=post.pk).order_by("pk").only("pk","post_type","title").first()
    prev_post = Post.objects.filter(pk__lt=post.pk).order_by("-pk").only("pk","post_type","title").first()

    # Optional tiny “deck” to preload thumbnails/posters on mobile
    deck = list(
        Post.objects.filter(Q(pk=post.pk) | Q(pk=getattr(next_post, "pk", None)) | Q(pk=getattr(prev_post, "pk", None)))
            .select_related("author").prefetch_related("images","videos")[:3]
    )

    similar_artworks = post.similar_artworks.all()[:10] if hasattr(post, "similar_artworks") else []
    is_following = (
        request.user.is_authenticated
        and request.user != post.author
        and Follow.objects.filter(follower=request.user, following=post.author).exists()
    )

    ctx = {
        "post": post,
        "nav_active": None,
        "likes_count": post.likes,
        "comments_count": post.comments.count(),
        "saves_count": post.bookmarks,
        "views_count": post.views,
        "is_liked_by_user": is_liked,
        "is_saved_by_user": is_saved,
        "is_suggested_by_user": is_suggested,
        "comments": post.comments.select_related("author").order_by("-created_at")[:50],
        "similar_artworks": similar_artworks,
        "is_following_author": is_following,

        # NEW
        "next_post": next_post,
        "prev_post": prev_post,
        "deck": deck,
    }
    return render(request, "posts/single_post.html", ctx)

@login_required
@transaction.atomic
def toggle_like(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    post = get_object_or_404(Post, pk=pk)
    liked = Like.objects.filter(user=request.user, post=post).first()
    if liked:
        liked.delete()
        Post.objects.filter(pk=post.pk).update(likes=F("likes") - 1)
        post.refresh_from_db(fields=["likes"])
        return JsonResponse({"liked": False, "likes": post.likes})
    else:
        Like.objects.create(user=request.user, post=post)
        Post.objects.filter(pk=post.pk).update(likes=F("likes") + 1)
        post.refresh_from_db(fields=["likes"])
        return JsonResponse({"liked": True, "likes": post.likes})

@login_required
@transaction.atomic
def toggle_save(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    post = get_object_or_404(Post, pk=pk)
    saved = Bookmark.objects.filter(user=request.user, post=post).first()
    if saved:
        saved.delete()
        Post.objects.filter(pk=post.pk).update(bookmarks=F("bookmarks") - 1)
        post.refresh_from_db(fields=["bookmarks"])
        return JsonResponse({"saved": False, "saves": post.bookmarks})
    else:
        Bookmark.objects.create(user=request.user, post=post)
        Post.objects.filter(pk=post.pk).update(bookmarks=F("bookmarks") + 1)
        post.refresh_from_db(fields=["bookmarks"])
        return JsonResponse({"saved": True, "saves": post.bookmarks})

@login_required
@transaction.atomic
def add_comment(request, pk):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    post = get_object_or_404(Post, pk=pk)
    body = (request.POST.get("body") or "").strip()
    if not body:
        return HttpResponseBadRequest("Empty comment")
    Comment.objects.create(post=post, author=request.user, body=body)
    return JsonResponse({"ok": True, "comments": post.comments.count()})



@login_required
@require_POST
def post_add_comment(request, pk):
    """Create a comment (or reply) and return to #comments tab."""
    post = get_object_or_404(Post, pk=pk)
    body = (request.POST.get("body") or "").strip()
    parent_id = request.POST.get("parent_id")
    parent = None
    if parent_id:
        parent = Comment.objects.filter(pk=parent_id, post=post).first()

    if body:
        Comment.objects.create(
            post=post,
            author=request.user,
            body=body,
            parent=parent,
        )
    return redirect(reverse("single_post", args=[post.pk]) + "#comments")
