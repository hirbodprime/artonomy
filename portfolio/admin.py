from django.contrib import admin
from .models import (
    PortfolioTheme, UserPortfolio, Profile, SocialLink,
    Artwork, ServiceItem, StatCounter, Skill, Education, Experience, Testimonial,ThemeLicense
)
from django.contrib import admin, messages
from django.db import transaction




@admin.register(PortfolioTheme)
class PortfolioThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "is_premium", "price_cents")
    list_editable = ("is_active", "is_premium", "price_cents")
    search_fields = ("name", "slug")
    list_filter = ("is_active", "is_premium")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

@admin.register(ThemeLicense)
class ThemeLicenseAdmin(admin.ModelAdmin):
    list_display = ("user", "theme", "purchased_at", "expires_at", "is_active_now")
    list_filter = ("theme",)
    search_fields = ("user__username", "user__email", "theme__name")
    def is_active_now(self, obj): return obj.is_active
    is_active_now.boolean = True
    is_active_now.short_description = "Active?"

@admin.register(UserPortfolio)
class UserPortfolioAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "theme", "is_primary", "is_published", "updated_at")
    list_editable = ("is_published",)
    list_filter = ("is_primary", "is_published", "theme")
    search_fields = ("user__username", "user__email", "title", "theme__name")
    ordering = ("-is_primary", "-updated_at")
    readonly_fields = ("created_at", "updated_at")

    actions = ["make_primary", "mark_published", "mark_unpublished"]

    @admin.action(description="Make selected portfolio(s) PRIMARY (one per user)")
    def make_primary(self, request, queryset):
        updated = 0
        with transaction.atomic():
            for site in queryset.select_related("user"):
                UserPortfolio.objects.filter(user=site.user, is_primary=True).exclude(pk=site.pk).update(is_primary=False)
                if not site.is_primary:
                    site.is_primary = True
                    site.save(update_fields=["is_primary", "updated_at"])
                    updated += 1
        if updated:
            self.message_user(request, f"Set {updated} portfolio(s) as primary.", level=messages.SUCCESS)
        else:
            self.message_user(request, "Nothing changed.", level=messages.INFO)

    @admin.action(description="Publish selected")
    def mark_published(self, request, queryset):
        self.message_user(request, f"Published {queryset.update(is_published=True)} portfolio(s).", level=messages.SUCCESS)

    @admin.action(description="Unpublish selected")
    def mark_unpublished(self, request, queryset):
        self.message_user(request, f"Unpublished {queryset.update(is_published=False)} portfolio(s).", level=messages.SUCCESS)


class SocialLinkInline(admin.TabularInline):
    model = SocialLink
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "phone", "location")
    inlines = [SocialLinkInline]


@admin.register(Artwork)
class ArtworkAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "is_published", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title", "caption")


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "created_at")
    search_fields = ("title", "description")


@admin.register(StatCounter)
class StatCounterAdmin(admin.ModelAdmin):
    list_display = ("owner", "label", "value")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("owner", "name", "percent")
    search_fields = ("name",)


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("owner", "school", "degree", "start_year", "end_year")


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("owner", "company", "title", "start_year", "end_year", "location")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("owner", "author_name", "role")
    search_fields = ("author_name", "role", "text")
