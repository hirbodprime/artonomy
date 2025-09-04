# admin.py
from django.contrib import admin
from .models import (Post, Category, Tool, Inspiration, Tag, Comment,
                     TextChapter, PostImage, PostVideo)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    search_fields = ("name",)

@admin.register(Inspiration)
class InspirationAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)

class TextChapterInline(admin.TabularInline):
    model = TextChapter
    extra = 1
    fields = ("order", "title", "content")
    ordering = ("order", "id")

class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 0
    fields = ("order", "image", "caption")
    ordering = ("order", "id")

class PostVideoInline(admin.TabularInline):
    model = PostVideo
    extra = 0
    fields = ("order", "file", "poster", "duration")
    ordering = ("order", "id")

class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    fields = ("author", "body", "parent", "likes")
    autocomplete_fields = ("author", "parent")

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "post_type", "created_at", "likes", "views")
    list_filter = ("post_type", "categories", "created_at")
    search_fields = ("title", "caption", "author__username")
    autocomplete_fields = ("author",)
    filter_horizontal = ("categories", "tools", "inspirations", "tags", "similar_artworks")
    inlines = [TextChapterInline, PostImageInline, PostVideoInline, CommentInline]
    fieldsets = (
        ("Basic Info", {"fields": ("author", "title", "caption", "post_type")}),
        ("Content (MVP single fields)", {"fields": ("body", "image", "video","cover"),
         "description": "Use chapters for TEXT. Multi-image/video inlines are below."}),
        ("Relations", {"fields": ("categories", "tools", "inspirations", "tags", "similar_artworks")}),
        ("Stats", {"fields": ("views", "likes", "shares", "bookmarks","is_draft")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at")

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author", "post", "body", "parent", "likes", "created_at")
    list_filter = ("created_at", "post")
    search_fields = ("body", "author__username")
    autocomplete_fields = ("post", "author", "parent")
