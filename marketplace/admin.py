from django.contrib import admin
from .models import MarketItem, MarketFavorite

@admin.register(MarketItem)
class MarketItemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "seller", "category", "price", "currency", "status", "views", "favorites", "created_at")
    list_filter  = ("status", "category", "currency", "created_at")
    search_fields = ("title", "description", "seller__username")

@admin.register(MarketFavorite)
class MarketFavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "item", "created_at")
    search_fields = ("user__username", "item__title")
