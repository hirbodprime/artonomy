# dashboard/views.py
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Q
from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth import get_user_model

# === Accounts ===
from accounts.models import Category as AccountsCategory, User

# === Posts ===
from posts.models import Post, TextChapter, Comment, Like, Bookmark, Category as PostsCategory

# === Network ===
from network.models import Follow

# === Marketplace ===
from marketplace.models import MarketItem, MarketFavorite

# === Collab ===
from collab.models import ServiceRequest, Conversation, Message, Notification

# === Suggest ===
from suggest.models import Suggestion, ExplorePin


@staff_member_required
def admin_overview(request):
    now = timezone.now()
    today = timezone.localdate()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # ---- Users
    total_users = User.objects.count()
    artists = User.objects.filter(role=User.Role.ARTIST).count()
    audience = User.objects.filter(role=User.Role.AUDIENCE).count()

    # created in ranges (if you keep date_joined from AbstractUser)
    users_last_24h = User.objects.filter(date_joined__gte=last_24h).count()
    users_last_7d = User.objects.filter(date_joined__gte=last_7d).count()

    # ---- Follows
    total_follows = Follow.objects.count()

    # ---- Posts
    total_posts = Post.objects.count()
    posts_by_type = (
        Post.objects
        .values('post_type')
        .annotate(c=Count('id'))
        .order_by('-c')
    )
    text_posts = Post.objects.filter(post_type=Post.PostType.TEXT).count()
    photo_posts = Post.objects.filter(post_type=Post.PostType.PHOTO).count()
    video_posts = Post.objects.filter(post_type=Post.PostType.VIDEO).count()
    drafts = Post.objects.filter(is_draft=True).count()

    posts_last_24h = Post.objects.filter(created_at__gte=last_24h).count()
    posts_last_7d = Post.objects.filter(created_at__gte=last_7d).count()

    # Engagement sums (from Post counters)
    total_likes = Post.objects.aggregate(s=Sum('likes'))['s'] or 0
    total_bookmarks = Post.objects.aggregate(s=Sum('bookmarks'))['s'] or 0
    total_comments = Comment.objects.count()
    total_views = Post.objects.aggregate(s=Sum('views'))['s'] or 0
    total_shares = Post.objects.aggregate(s=Sum('shares'))['s'] or 0

    # Top categories (by post count)
    top_post_categories = (
        PostsCategory.objects
        .annotate(post_count=Count('posts'))
        .order_by('-post_count')[:10]
    )

    # Recent objects
    recent_posts = (
        Post.objects
        .select_related('author')
        .order_by('-created_at')[:10]
    )
    recent_users = (
        User.objects
        .order_by('-date_joined')[:10]
    )

    # ---- Marketplace
    market_total = MarketItem.objects.count()
    market_status = (
        MarketItem.objects
        .values('status')
        .annotate(c=Count('id'))
        .order_by('-c')
    )
    market_favorites = MarketFavorite.objects.count()

    # ---- Collab
    req_total = ServiceRequest.objects.count()
    req_by_status = (
        ServiceRequest.objects
        .values('status')
        .annotate(c=Count('id'))
        .order_by('-c')
    )
    convo_total = Conversation.objects.count()
    msg_total = Message.objects.count()
    msg_last_24h = Message.objects.filter(created_at__gte=last_24h).count()
    notif_total = Notification.objects.count()
    notif_unread = Notification.objects.filter(is_read=False).count()

    # ---- Suggestions / Explore
    suggestion_total = Suggestion.objects.count()
    pins_today = ExplorePin.objects.filter(date=today).count()
    pins_total = ExplorePin.objects.count()

    # Cross-app categories note (you have both accounts.Category and posts.Category)
    accounts_categories = AccountsCategory.objects.count()
    posts_categories = PostsCategory.objects.count()

    context = {
        # Time refs
        'now': now,
        'today': today,
        'last_24h': last_24h,
        'last_7d': last_7d,

        # Users
        'total_users': total_users,
        'artists': artists,
        'audience': audience,
        'users_last_24h': users_last_24h,
        'users_last_7d': users_last_7d,
        'recent_users': recent_users,

        # Network
        'total_follows': total_follows,

        # Posts
        'total_posts': total_posts,
        'posts_by_type': list(posts_by_type),
        'text_posts': text_posts,
        'photo_posts': photo_posts,
        'video_posts': video_posts,
        'drafts': drafts,
        'posts_last_24h': posts_last_24h,
        'posts_last_7d': posts_last_7d,
        'total_likes': total_likes,
        'total_bookmarks': total_bookmarks,
        'total_comments': total_comments,
        'total_views': total_views,
        'total_shares': total_shares,
        'top_post_categories': top_post_categories,
        'recent_posts': recent_posts,

        # Marketplace
        'market_total': market_total,
        'market_status': list(market_status),
        'market_favorites': market_favorites,

        # Collab
        'req_total': req_total,
        'req_by_status': list(req_by_status),
        'convo_total': convo_total,
        'msg_total': msg_total,
        'msg_last_24h': msg_last_24h,
        'notif_total': notif_total,
        'notif_unread': notif_unread,

        # Suggest / Explore
        'suggestion_total': suggestion_total,
        'pins_today': pins_today,
        'pins_total': pins_total,

        # Categories (both systems)
        'accounts_categories': accounts_categories,
        'posts_categories': posts_categories,
    }
    return render(request, 'dashboard/admin_overview.html', context)
