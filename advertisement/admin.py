from django.contrib import admin
from .models import HomepageAd

@admin.register(HomepageAd)
class HomepageAdAdmin(admin.ModelAdmin):
    list_display = ("title", "position", "is_active", "starts_at", "ends_at")
    list_filter = ("is_active",)
    search_fields = ("title", "subtitle")
