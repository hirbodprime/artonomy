# suggest/admin.py
from django.contrib import admin
from .models import Suggestion,ExplorePin

@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    list_display = ("id", "suggester", "post", "created_at")
    list_filter = ("created_at",)
    search_fields = ("suggester__username", "post__title", "post__author__username")
    autocomplete_fields = ("suggester", "post")


@admin.register(ExplorePin)
class ExplorePinAdmin(admin.ModelAdmin):
    list_display = ('date', 'post', 'created_at')
    list_filter = ('date',)
    search_fields = ('post__title', 'post__author__username')
