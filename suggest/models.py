# suggest/models.py
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Index
from django.utils import timezone

from posts.models import Post  # adjust import if your posts app path differs

User = settings.AUTH_USER_MODEL


class Suggestion(models.Model):
    """
    One user suggests someone else's post. These suggestions show on the suggester's profile.
    """
    suggester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="suggestions_made")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="suggestions")
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        unique_together = ("suggester", "post")
        indexes = [
            Index(fields=["suggester"]),
            Index(fields=["post"]),
            Index(fields=["created_at"]),
        ]
        ordering = ("-created_at",)

    def clean(self):
        # prevent suggesting your own post
        # (can’t be expressed as a DB CheckConstraint because it would require a join)
        if self.post_id and self.suggester_id and self.post.author_id == self.suggester_id:
            raise ValidationError("You cannot suggest your own post.")

    def save(self, *args, **kwargs):
        self.full_clean()  # ensures clean() runs even when created via code
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.suggester} suggested Post#{self.post_id}"


class ExplorePin(models.Model):
    """
    Stores which post is pinned for a given day (global, not per-category).
    Exactly 4 rows per date when available.
    """
    date = models.DateField(db_index=True, default=timezone.localdate)
    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, related_name='explore_pins')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('date', 'post')
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['post']),
        ]
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date} → Post#{self.post_id}"