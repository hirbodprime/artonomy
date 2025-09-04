# models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import F
User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)  # NEW
    def __str__(self): return self.name

class Post(models.Model):
    class PostType(models.TextChoices):
        TEXT = "TEXT", "Text"
        PHOTO = "PHOTO", "Photo"
        VIDEO = "VIDEO", "Video"

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    title = models.CharField(max_length=200)
    caption = models.TextField(blank=True)
    post_type = models.CharField(max_length=10, choices=PostType.choices)

    # MVP single media (kept for compatibility)
    image = models.ImageField(upload_to="posts/images/", blank=True, null=True)
    video = models.FileField(upload_to="posts/videos/", blank=True, null=True)
    body  = models.TextField(blank=True, null=True)  # optional for text posts
    cover = models.ImageField(upload_to="post_covers/", blank=True, null=True)

    # Relations
    categories = models.ManyToManyField(Category, related_name="posts", blank=True)
    similar_artworks = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="related_posts")

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Stats
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    shares = models.PositiveIntegerField(default=0)
    bookmarks = models.PositiveIntegerField(default=0)
    artwork_length = models.CharField(max_length=50, blank=True)
    is_draft = models.BooleanField(default=False)
    
    def __str__(self): return f"{self.title} ({self.post_type})"


# ---- NOW: Chapters for TEXT posts ----
class TextChapter(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="chapters")
    order = models.PositiveIntegerField(default=1, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]  # stable ordering

    def __str__(self): return f"{self.post_id} · {self.order} · {self.title or 'Chapter'}"


# ---- LATER (optional): multi-media, safe to add anytime ----
class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="posts/images/")
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=1, db_index=True)
    class Meta: ordering = ["order", "id"]

class PostVideo(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="videos")
    file = models.FileField(upload_to="posts/videos/")
    poster = models.ImageField(upload_to="posts/video_posters/", blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1, db_index=True)
    class Meta: ordering = ["order", "id"]


# Tools / Inspirations / Tags / Comments (unchanged)
class Tool(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)
    def __str__(self): return self.name

class Inspiration(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

Post.add_to_class("tools", models.ManyToManyField(Tool, blank=True, related_name="posts"))
Post.add_to_class("inspirations", models.ManyToManyField(Inspiration, blank=True, related_name="posts"))
Post.add_to_class("tags", models.ManyToManyField(Tag, blank=True, related_name="posts"))

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    likes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Comment by {self.author} on {self.post}"




class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes")
    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="like_set")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("user", "post")

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")
    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="bookmark_set")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ("user", "post")

# handy properties (optional)
def _likes_count(self): return self.likes
def _bookmarks_count(self): return self.bookmarks
def _comments_count(self): return self.comments.count()
Post.likes_count = property(_likes_count)
Post.bookmarks_count = property(_bookmarks_count)
Post.comments_count = property(_comments_count)