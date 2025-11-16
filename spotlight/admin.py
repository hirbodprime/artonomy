from django.contrib import admin
from .models import (
    SpotlightSettings,
    StarTransaction,
    Referral,
    SpotlightBoost,
)


@admin.register(SpotlightSettings)
class SpotlightSettingsAdmin(admin.ModelAdmin):
    list_display = ["star_name", "referral_reward", "invited_reward", "spotlight_cost", "spotlight_hours"]
    list_editable = ["referral_reward", "invited_reward", "spotlight_cost", "spotlight_hours"]
    readonly_fields = ["id"]
    fieldsets = (
        (None, {
            "fields": ("star_name", "referral_reward", "invited_reward", "spotlight_cost", "spotlight_hours")
        }),
    )

    def has_add_permission(self, request):
        # Only one settings instance allowed
        return not SpotlightSettings.objects.exists() or super().has_add_permission(request)


@admin.register(StarTransaction)
class StarTransactionAdmin(admin.ModelAdmin):
    list_display = ["profile", "amount", "reason", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["profile__user__username", "reason"]
    date_hierarchy = "created_at"
    autocomplete_fields = ["profile"]


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ["inviter", "invited", "created_at", "rewarded"]
    list_filter = ["rewarded", "created_at"]
    search_fields = ["inviter__user__username", "invited__user__username"]
    autocomplete_fields = ["inviter", "invited"]
    actions = ["mark_rewarded"]

    @admin.action(description="Mark selected referrals as rewarded")
    def mark_rewarded(self, request, queryset):
        updated = queryset.update(rewarded=True)
        self.message_user(request, f"{updated} referral(s) marked as rewarded.")


@admin.register(SpotlightBoost)
class SpotlightBoostAdmin(admin.ModelAdmin):
    list_display = ["profile", "expires_at", "active"]
    list_filter = ["expires_at"]
    search_fields = ["profile__user__username"]
    autocomplete_fields = ["profile"]
    readonly_fields = ["active"]
