# marketplace/admin.py
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, F
from django.utils import timezone

from .models import (
    MarketplaceStats,
    BusinessProfile,
    JoinRequest,
    Product,
)

# ---------- Small helpers ----------

def _img_thumb(filefield, size=60):
    """Safe thumbnail renderer for admin list/previews."""
    try:
        if filefield and getattr(filefield, "url", None):
            return format_html(
                '<img src="{}" alt="" style="width:{}px;height:{}px;'
                'object-fit:cover;border-radius:8px;border:1px solid rgba(0,0,0,.08)"/>',
                filefield.url, size, size
            )
    except Exception:
        pass
    return format_html('<span style="color:#888">—</span>')


# ---------- Inlines ----------

class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = ("title", "is_service", "price", "currency", "status", "views")
    classes = ("collapse",)


# ---------- Custom Filters ----------

class LiveStatusFilter(admin.SimpleListFilter):
    title = _("Live status")
    parameter_name = "live"

    def lookups(self, request, model_admin):
        return (
            ("1", _("Live (approved + active sub)")),
            ("0", _("Not live")),
        )

    def queryset(self, request, qs):
        val = self.value()
        if val == "1":
            now = timezone.now()
            return qs.filter(is_approved=True, subscription_expires_at__gt=now)
        if val == "0":
            # Anything not matching the live definition
            now = timezone.now()
            return qs.exclude(is_approved=True, subscription_expires_at__gt=now)
        return qs


# ---------- ModelAdmins ----------

@admin.register(MarketplaceStats)
class MarketplaceStatsAdmin(admin.ModelAdmin):
    list_display = ("name", "join_clicks")
    search_fields = ("name",)
    actions = ("reset_clicks",)

    @admin.action(description=_("Reset join clicks to 0"))
    def reset_clicks(self, request, queryset):
        updated = queryset.update(join_clicks=0)
        self.message_user(request, _(f"Reset join_clicks for {updated} row(s)."), level=messages.SUCCESS)


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = (
        "display_name", "kind", "owner",
        "is_approved", "is_live_badge",
        "subscription_expires_at", "product_count",
        "created_at", "avatar_thumb",
    )
    list_filter = ("kind", "is_approved", LiveStatusFilter, ("created_at", admin.DateFieldListFilter))
    search_fields = (
        "display_name",
        "slug",
        "owner__username",
        "owner__email",
        "tagline",
        "location",
    )
    readonly_fields = ("created_at", "avatar_preview", "cover_preview", "slug")
    inlines = (ProductInline,)
    ordering = ("-is_approved", "-created_at")
    fieldsets = (
        (_("Identity"), {
            "fields": (
                "owner", "kind", "display_name", "slug", "tagline", "bio_long",
            )
        }),
        (_("Media"), {
            "fields": ("avatar", "avatar_preview", "cover", "cover_preview"),
        }),
        (_("Meta & Visibility"), {
            "fields": ("location", "is_approved", "trial_started_at", "subscription_expires_at", "created_at"),
        }),
    )
    actions = (
        "action_approve",
        "action_unapprove",
        "action_start_trial_2d",
        "action_extend_1m",
        "action_extend_3m",
        "action_extend_12m",
    )

    # annotate counts
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_product_count=Count("products"))

    @admin.display(ordering="_product_count", description=_("Products"))
    def product_count(self, obj):
        return getattr(obj, "_product_count", 0)

    @admin.display(description=_("Avatar"))
    def avatar_thumb(self, obj):
        return _img_thumb(obj.avatar, size=40)

    @admin.display(description=_("Avatar preview"))
    def avatar_preview(self, obj):
        return _img_thumb(obj.avatar, size=120)

    @admin.display(description=_("Cover preview"))
    def cover_preview(self, obj):
        return _img_thumb(obj.cover, size=160)

    @admin.display(boolean=True, description=_("Live"))
    def is_live_badge(self, obj):
        return obj.is_live()

    # ----- bulk actions -----

    @admin.action(description=_("Approve selected profiles"))
    def action_approve(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, _(f"Approved {updated} profile(s)."), level=messages.SUCCESS)

    @admin.action(description=_("Unapprove selected profiles"))
    def action_unapprove(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, _(f"Unapproved {updated} profile(s)."), level=messages.WARNING)

    @admin.action(description=_("Start free trial (2 days) and auto-approve"))
    def action_start_trial_2d(self, request, queryset):
        count = 0
        for bp in queryset:
            bp.start_free_trial(days=2, auto_approve=True)
            count += 1
        self.message_user(request, _(f"Started 2-day trial for {count} profile(s)."), level=messages.SUCCESS)

    @admin.action(description=_("Extend subscription by 1 month"))
    def action_extend_1m(self, request, queryset):
        count = 0
        for bp in queryset:
            bp.extend_subscription(months=1)
            count += 1
        self.message_user(request, _(f"Extended {count} profile(s) by 1 month."), level=messages.SUCCESS)

    @admin.action(description=_("Extend subscription by 3 months"))
    def action_extend_3m(self, request, queryset):
        count = 0
        for bp in queryset:
            bp.extend_subscription(months=3)
            count += 1
        self.message_user(request, _(f"Extended {count} profile(s) by 3 months."), level=messages.SUCCESS)

    @admin.action(description=_("Extend subscription by 12 months"))
    def action_extend_12m(self, request, queryset):
        count = 0
        for bp in queryset:
            bp.extend_subscription(months=12)
            count += 1
        self.message_user(request, _(f"Extended {count} profile(s) by 12 months."), level=messages.SUCCESS)


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "profile", "status", "created_at")
    list_filter = ("status", ("created_at", admin.DateFieldListFilter))
    search_fields = (
        "user__username", "user__email",
        "profile__display_name", "profile__slug",
    )
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    actions = ("approve_selected", "reject_selected")

    @admin.action(description=_("Approve selected requests (and publish profiles)"))
    def approve_selected(self, request, queryset):
        changed = 0
        for jr in queryset.select_related("profile"):
            if jr.status != JoinRequest.Status.APPROVED:
                jr.status = JoinRequest.Status.APPROVED
                jr.save(update_fields=["status"])
                if not jr.profile.is_approved:
                    jr.profile.is_approved = True
                    jr.profile.save(update_fields=["is_approved"])
                changed += 1
        self.message_user(request, _(f"Approved {changed} request(s)."), level=messages.SUCCESS)

    @admin.action(description=_("Reject selected requests (profiles remain unapproved)"))
    def reject_selected(self, request, queryset):
        updated = queryset.exclude(status=JoinRequest.Status.REJECTED).update(status=JoinRequest.Status.REJECTED)
        self.message_user(request, _(f"Rejected {updated} request(s)."), level=messages.WARNING)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title", "profile", "category",
        "price", "currency",
        "is_service", "status", "views",
        "image_thumb", "created_at",
    )
    list_filter = (
        "status", "is_service", "currency", "category",
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "title", "description",
        "profile__display_name", "profile__slug",
        "category__name", "category__name_fa",
    )
    readonly_fields = ("created_at", "image_preview")
    ordering = ("-created_at", "-id")
    fieldsets = (
        (_("Belongs to"), {"fields": ("profile",)}),
        (_("Content"), {"fields": ("title", "description", "category", "is_service")}),
        (_("Pricing"), {"fields": ("price", "currency")}),
        (_("Media & Status"), {"fields": ("image", "image_preview", "status", "views", "created_at")}),
    )
    actions = ("mark_active", "mark_draft", "mark_sold")

    @admin.display(description=_("Image"))
    def image_thumb(self, obj):
        return _img_thumb(obj.image, size=44)

    @admin.display(description=_("Image preview"))
    def image_preview(self, obj):
        return _img_thumb(obj.image, size=160)

    # bulk actions
    @admin.action(description=_("Mark selected as Active"))
    def mark_active(self, request, queryset):
        updated = queryset.update(status=Product.Status.ACTIVE)
        self.message_user(request, _(f"Updated {updated} product(s) to Active."), level=messages.SUCCESS)

    @admin.action(description=_("Mark selected as Draft"))
    def mark_draft(self, request, queryset):
        updated = queryset.update(status=Product.Status.DRAFT)
        self.message_user(request, _(f"Updated {updated} product(s) to Draft."), level=messages.INFO)

    @admin.action(description=_("Mark selected as Sold"))
    def mark_sold(self, request, queryset):
        updated = queryset.update(status=Product.Status.SOLD)
        self.message_user(request, _(f"Updated {updated} product(s) to Sold."), level=messages.WARNING)
# marketplace/admin.py
from django.contrib import admin
from .models import SubscriptionPayment
from django.contrib import admin
from .models import SubscriptionPayment

@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "profile",
        "owner",            # ✅ derived from profile.owner
        "status",
        "amount",
        "currency",
        "months_granted",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = (
        "profile__display_name",
        "profile__owner__username",
        "profile__owner__email",
    )
    readonly_fields = ("created_at", "previous_expires_at", "new_expires_at", "reviewed_at", "reviewed_by")

    def owner(self, obj):
        return obj.profile.owner
    owner.short_description = "Owner"
    owner.admin_order_field = "profile__owner"
