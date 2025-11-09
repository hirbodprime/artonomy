# artists/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Subcategory


# ───────────── Inlines ─────────────

class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 1
    fields = ("name", "slug", "order", "image", "image_preview")
    readonly_fields = ("image_preview",)
    ordering = ("order", "name")

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:60px;max-width:120px;object-fit:cover;border-radius:6px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = "پیش‌نمایش"


# ───────────── CategoryAdmin ─────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "order",
        "subcategories_count",
        "image_preview",
    )
    list_display_links = ("name",)
    list_editable = ("order",)
    search_fields = ("name", "slug")
    ordering = ("order", "name")
    readonly_fields = ("image_preview",)
    inlines = [SubcategoryInline]

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "order")
        }),
        ("تصویر", {
            "fields": ("image", "image_preview")
        }),
    )

    def subcategories_count(self, obj):
        return obj.subcategories.count()
    subcategories_count.short_description = "تعداد زیرشاخه‌ها"

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:160px;object-fit:cover;border-radius:8px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = "پیش‌نمایش"


# ───────────── SubcategoryAdmin ─────────────

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "order", "image_preview")
    list_filter = ("category",)
    search_fields = ("name", "slug", "category__name")
    ordering = ("category__order", "order", "name")
    readonly_fields = ("image_preview",)

    fieldsets = (
        (None, {
            "fields": ("category", "name", "slug", "order")
        }),
        ("تصویر", {
            "fields": ("image", "image_preview")
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:160px;object-fit:cover;border-radius:8px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = "پیش‌نمایش"
