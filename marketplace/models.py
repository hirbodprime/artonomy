# marketplace/models.py
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from posts.models import Category
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class MarketItem(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DRAFT  = "DRAFT",  "Draft"
        SOLD   = "SOLD",   "Sold"

    class PricingType(models.TextChoices):
        NEGOTIABLE = "NEGOTIABLE", _("Negotiable")
        FIXED      = "FIXED",      _("Fixed")
        RANGE      = "RANGE",      _("Range")

    seller      = models.ForeignKey(User, on_delete=models.CASCADE, related_name="market_items")
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    category    = models.ForeignKey(
        Category, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="market_items"
    )

    # Pricing
    pricing_type = models.CharField(
        max_length=12, choices=PricingType.choices, default=PricingType.NEGOTIABLE
    )
    price        = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    price_min    = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_max    = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency     = models.CharField(max_length=12, default="TOMAN")

    image     = models.ImageField(upload_to="market/items/", blank=True, null=True)

    status    = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    views     = models.PositiveIntegerField(default=0)
    favorites = models.PositiveIntegerField(default=0)  # kept for compatibility

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.title} · {self.seller}"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE

    # Helpers to unify sorting/filtering across types
    @property
    def effective_min_price(self):
        if self.pricing_type == self.PricingType.FIXED:
            return self.price
        if self.pricing_type == self.PricingType.RANGE and self.price_min is not None:
            return self.price_min
        return Decimal("0.00")

    @property
    def effective_max_price(self):
        if self.pricing_type == self.PricingType.FIXED:
            return self.price
        if self.pricing_type == self.PricingType.RANGE and self.price_max is not None:
            return self.price_max
        # negotiable: treat as extremely large for some uses, but we won't rely on this in DB filtering
        return self.price or Decimal("0.00")

class MarketFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="market_favorites")
    item = models.ForeignKey(MarketItem, on_delete=models.CASCADE, related_name="favorite_set")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "item")
