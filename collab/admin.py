from django.contrib import admin
from .models import ServiceRequest, Conversation, Message, Notification

# @admin.register(ServiceRequest)
# class ServiceRequestAdmin(admin.ModelAdmin):
#     list_display = ("id","item","requester","provider","status","created_at")
#     list_filter  = ("status",)
#     search_fields = ("brief","requester__username","provider__username")

# @admin.register(Conversation)
# class ConversationAdmin(admin.ModelAdmin):
#     list_display = ("id","item","user_a","user_b","is_active","created_at")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id","conversation","sender","created_at")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id","user","kind","is_read","created_at")
    list_filter  = ("kind","is_read")
