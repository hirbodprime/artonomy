from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Profile,
    ProfileCounter,
    Skill,
    Testimonial,
    SocialLink,
    ClientLogo,
)

# ───────────────────── Inlines ─────────────────────

class ProfileCounterInline(admin.TabularInline):
    model = ProfileCounter
    extra = 1
    fields = ("label", "value", "order")
    ordering = ("order", "id")


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1
    fields = ("name", "percent", "order")
    ordering = ("order", "id")


class TestimonialInline(admin.StackedInline):
    model = Testimonial
    extra = 0
    fields = (
        "person_name",
        "quote",
        "source_label",
        "source_url",
        "background_image",
        "preview_bg",
        "order",
    )
    readonly_fields = ("preview_bg",)
    ordering = ("order", "id")

    def preview_bg(self, obj):
        if obj.background_image:
            return format_html(
                '<img src="{}" style="max-width:220px;max-height:120px;'
                'border-radius:6px;border:1px solid #ddd;" />',
                obj.background_image.url,
            )
        return "—"
    preview_bg.short_description = "پیش‌نمایش پس‌زمینه"


class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 1
    fields = ("title", "url", "order")
    ordering = ("order", "id")


class ClientLogoInline(admin.TabularInline):
    model = ClientLogo
    extra = 1
    fields = ("title", "url", "image", "preview", "order")
    readonly_fields = ("preview",)
    ordering = ("order", "id")

    def preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:140px;max-height:60px;'
                'object-fit:contain;border-radius:6px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return "—"
    preview.short_description = "لوگو"


# ───────────────────── ProfileAdmin ─────────────────────

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = [
        ProfileCounterInline,
        SkillInline,
        TestimonialInline,
        SocialLinkInline,
        ClientLogoInline,
    ]

    list_display = (
        "user",
        "role",
        "category",
        "subcategory",
        "business_kind",
        "completion",
        "created_at",
    )
    list_filter = (
        "role",
        "business_kind",
        "category",
        "subcategory",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "header_title",
        "story_title",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "completion",
        "header_background_preview",
    )

    fieldsets = (
        ("کاربر", {
            "fields": (
                "user",
                "role",
                "category",
                "subcategory",
                "business_kind",
                "completion",
                "code",
            )
        }),
        ("هدر پروفایل", {
            "fields": (
                "header_background",
                "header_background_preview",
                "header_title",
                "header_subtitle",
            )
        }),
        ("داستان کوچک من", {
            "fields": (
                "story_title",
                "story_subtitle",
                "story_paragraph_1",
                "story_paragraph_2",
            )
        }),
        ("متادیتا", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    # ───────────── Preview helpers ─────────────

    def header_background_preview(self, obj):
        if obj.header_background:
            return format_html(
                '<img src="{}" style="max-width:260px;max-height:140px;'
                'border-radius:10px;border:1px solid #ddd;" />',
                obj.header_background.url,
            )
        return "—"
    header_background_preview.short_description = "پیش‌نمایش هدر"

    # ───────────── completion auto-refresh ─────────────

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.refresh_completion()

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.refresh_completion()


# ───────────────────── Other models (optional direct access) ─────────────────────

@admin.register(ProfileCounter)
class ProfileCounterAdmin(admin.ModelAdmin):
    list_display = ("profile", "label", "value", "order")
    list_filter = ("profile",)
    search_fields = ("profile__user__username", "label")
    ordering = ("profile", "order", "id")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("profile", "name", "percent", "order")
    list_filter = ("profile",)
    search_fields = ("profile__user__username", "name")
    ordering = ("profile", "order", "id")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("profile", "person_name", "source_label", "order")
    list_filter = ("profile",)
    search_fields = ("profile__user__username", "person_name", "quote", "source_label")
    ordering = ("profile", "order", "id")


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("profile", "title", "url", "order")
    list_filter = ("profile",)
    search_fields = ("profile__user__username", "title", "url")
    ordering = ("profile", "order", "id")


@admin.register(ClientLogo)
class ClientLogoAdmin(admin.ModelAdmin):
    list_display = ("profile", "title", "url", "order")
    list_filter = ("profile",)
    search_fields = ("profile__user__username", "title", "url")
    ordering = ("profile", "order", "id")
