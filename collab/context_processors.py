def notif_unread_count(request):
    if request.user.is_authenticated:
        try:
            return {"notif_unread_count": request.user.notifications.filter(is_read=False).count()}
        except Exception:
            return {"notif_unread_count": 0}
    return {"notif_unread_count": 0}
