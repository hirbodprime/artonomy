# marketplace/admin.py
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Product,
    ProductImage,
    Service,
    ServiceImage,
    ArtPost,
    ArtPostImage
)

admin.site.register(ArtPost)
admin.site.register(ArtPostImage)
# ───────────── Inlines ─────────────

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "image_preview", "alt_text", "order", "is_primary")
    readonly_fields = ("image_preview",)
    ordering = ("order", "id")

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:140px;object-fit:cover;border-radius:6px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = "پیش‌نمایش"


class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1
    fields = ("image", "image_preview", "alt_text", "order", "is_primary")
    readonly_fields = ("image_preview",)
    ordering = ("order", "id")

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:140px;object-fit:cover;border-radius:6px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = "پیش‌نمایش"


# ───────────── ProductAdmin ─────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]

    list_display = (
        "title",
        "profile",
        "display_price",
        "condition",
        "currency",
        "quantity",
        "is_active",
        "order",
        "updated_at",
    )
    list_filter = (
        "is_active",
        "condition",
        "currency",
        "profile__role",  # اگر Profile.role هست
    )
    search_fields = (
        "title",
        "slug",
        "description",
        "profile__user__username",
        "profile__user__email",
    )
    list_editable = ("is_active", "order")
    ordering = ("order", "-updated_at", "-id")
    raw_id_fields = ("profile",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("profile", "title", "slug", "description")
        }),
        ("قیمت و موجودی", {
            "fields": (
                "price_type",
                "price_amount",
                "currency",
                "quantity",
                "condition",
                "is_active",
                "order",
            )
        }),
        ("تصویر تکی قدیمی (اختیاری)", {
            "classes": ("collapse",),
            "fields": ("image",),
        }),
        ("زمان‌ها", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    def save_model(self, request, obj, form, change):
        # if you ever want: auto-slug from title on change:
        # if not obj.slug:
        #     from django.utils.text import slugify
        #     obj.slug = slugify(obj.title, allow_unicode=True)
        super().save_model(request, obj, form, change)


# ───────────── ProductImageAdmin (optional direct access) ─────────────

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "order", "is_primary", "image_preview")
    list_filter = ("is_primary", "product__profile")
    search_fields = ("product__title", "alt_text")
    ordering = ("product", "order", "id")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:140px;object-fit:cover;border-radius:6px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = "پیش‌نمایش"


# ───────────── ServiceAdmin ─────────────

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    inlines = [ServiceImageInline]

    list_display = (
        "title",
        "profile",
        "display_price",
        "pricing_model",
        "currency",
        "is_active",
        "order",
        "updated_at",
    )
    list_filter = (
        "is_active",
        "pricing_model",
        "currency",
        "profile__role",
    )
    search_fields = (
        "title",
        "slug",
        "description",
        "tags",
        "profile__user__username",
        "profile__user__email",
    )
    list_editable = ("is_active", "order")
    ordering = ("order", "-updated_at", "-id")
    raw_id_fields = ("profile",)
    readonly_fields = ("created_at", "updated_at", "tag_list_display")

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": ("profile", "title", "slug", "description", "image")
        }),
        ("برچسب‌ها", {
            "fields": ("tags", "tag_list_display")
        }),
        ("مدل قیمت‌گذاری", {
            "fields": (
                "pricing_model",
                "currency",
                "min_price",
                "max_price",
                "is_active",
                "order",
            )
        }),
        ("زمان‌ها", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    def tag_list_display(self, obj):
        return ", ".join(obj.tag_list())
    tag_list_display.short_description = "برچسب‌ها (لیست)"


# ───────────── ServiceImageAdmin (optional direct access) ─────────────

@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = ("service", "order", "is_primary", "image_preview")
    list_filter = ("is_primary", "service__profile")
    search_fields = ("service__title", "alt_text")
    ordering = ("service", "order", "id")
    readonly_fields = ("image_preview",)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:80px;max-width:140px;object-fit:cover;border-radius:6px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return "—"
    image_preview.short_description = "پیش‌نمایش"
