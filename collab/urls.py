from django.urls import path
from . import views

app_name = "collab"

urlpatterns = [
    # Requests / actions
    path("request/<int:item_id>/create/", views.request_create, name="request_create"),
    path("request/<int:req_id>/accept/", views.request_accept_by_provider, name="provider_accept"),
    path("request/<int:req_id>/decline/", views.request_decline_by_provider, name="provider_decline"),
    path("request/<int:req_id>/confirm/", views.request_confirm_by_requester, name="requester_confirm"),

    # Notification center
    path("notifications/", views.notifications_center, name="notifications"),
    path("notifications/read/<int:pk>/", views.notification_mark_read, name="notif_read"),
    path("notifications/unread-count/", views.unread_count, name="unread_count"),

    # Chat
    path("chat/<int:conv_id>/", views.chat_view, name="chat"),
    path("chat/<int:conv_id>/send/", views.chat_send, name="chat_send"),
    path("chat/<int:conv_id>/poll/", views.chat_poll, name="chat_poll"),  # simple long-poll / short-poll
    
]
