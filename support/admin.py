from django.contrib import admin
from .models import SupportTicket

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "profile", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("subject", "message", "admin_reply", "profile__user__email")
    readonly_fields = ("created_at", "updated_at")
