from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model

# ⬇️ CHANGED: use Category from the posts app
from posts.models import Category   # <-- if your app is named differently, adjust (e.g., core.models)

User = get_user_model()


class MarketItem(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DRAFT  = "DRAFT",  "Draft"
        SOLD   = "SOLD",   "Sold"

    seller      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="market_items")
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # ⬇️ CHANGED: FK now points to posts.Category
    category    = models.ForeignKey(
        Category, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="market_items"
    )

    price     = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency  = models.CharField(max_length=12, default="Toman")
    image     = models.ImageField(upload_to="market/items/", blank=True, null=True)

    status    = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    views     = models.PositiveIntegerField(default=0)
    favorites = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.title} · {self.seller}"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class MarketFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="market_favorites")
    item = models.ForeignKey(MarketItem, on_delete=models.CASCADE, related_name="favorite_set")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "item")
