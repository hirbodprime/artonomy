from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET

# from marketplace.models import MarketItem
from .models import ServiceRequest, Conversation, Message, Notification
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

def _notify(*, user, kind, request=None, title="", body="", message=None):
    Notification.objects.create(
        user=user,
        kind=kind,
        request=request,
        title=title or (message or ""),
        body=body  or (message or ""),
        is_read=False,
    )


@login_required
@require_POST
def request_create(request, item_id):
    item = get_object_or_404(MarketItem, pk=item_id, status=MarketItem.Status.ACTIVE)
    if item.seller_id == request.user.id:
        return JsonResponse({"ok": False, "error": "You cannot request your own service."}, status=400)

    brief = (request.POST.get("brief") or "").strip()
    file  = request.FILES.get("attachment")

    if len(brief) < 8:
        return JsonResponse({"ok": False, "error": "Please describe your project (min 8 chars)."}, status=400)

    sr = ServiceRequest.objects.create(
        item=item, requester=request.user, provider=item.seller,
        brief=brief, attachments=file
    )

    # notify provider (→ REQUEST)
    _notify(
        user=item.seller,
        kind=Notification.Kind.REQUEST,
        request=sr,
        title="New service request",
        body=f"{request.user.username} requested: {item.title}",
    )

    return JsonResponse({"ok": True, "message": "Request sent."})


@login_required
@require_POST
def request_accept_by_provider(request, req_id):
    sr = get_object_or_404(ServiceRequest, pk=req_id)
    if sr.provider_id != request.user.id:
        return HttpResponseForbidden("Not allowed.")
    if sr.status != ServiceRequest.Status.PENDING_PROVIDER:
        return JsonResponse({"ok": False, "error": "Request is not pending."}, status=400)

    sr.status = ServiceRequest.Status.ACCEPTED_PROVIDER
    sr.save(update_fields=["status", "updated_at"])

    # notify requester (→ ACCEPT)
    _notify(
        user=sr.requester,
        kind=Notification.Kind.ACCEPT,
        request=sr,
        title="Provider accepted your request",
        body=f"{sr.provider.username} accepted. Please confirm to start chat.",
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
def request_decline_by_provider(request, req_id):
    sr = get_object_or_404(ServiceRequest, pk=req_id)
    if sr.provider_id != request.user.id:
        return HttpResponseForbidden("Not allowed.")
    sr.status = ServiceRequest.Status.DECLINED
    sr.save(update_fields=["status", "updated_at"])

    # still a request-related notification → use REQUEST
    _notify(
        user=sr.requester,
        kind=Notification.Kind.REQUEST,
        request=sr,
        title="Request declined",
        body=f"{sr.provider.username} declined your request.",
    )
    return JsonResponse({"ok": True})

@login_required
@require_POST
def request_confirm_by_requester(request, req_id):
    sr = get_object_or_404(ServiceRequest, pk=req_id)
    if sr.requester_id != request.user.id:
        return HttpResponseForbidden("Not allowed.")
    if sr.status != ServiceRequest.Status.ACCEPTED_PROVIDER:
        return JsonResponse({"ok": False, "error": "This request isn’t ready for confirmation."}, status=400)

    sr.status = ServiceRequest.Status.ACCEPTED_BOTH
    sr.save(update_fields=["status", "updated_at"])

    conv, _ = Conversation.objects.get_or_create(
        request=sr,
        defaults={"item": sr.item, "user_a": sr.requester, "user_b": sr.provider, "is_active": True},
    )

    # notify provider (→ CONFIRM)
    _notify(
        user=sr.provider,
        kind=Notification.Kind.CONFIRM,
        request=sr,
        title="Requester confirmed",
        body=f"{sr.requester.username} confirmed. Chat is open.",
    )
    return JsonResponse({"ok": True, "chat_url": f"/collab/chat/{conv.pk}/"})


# ----------------- Notification Center -----------------
# collab/views.py
from django.db.models import Q, Max

@login_required
def notifications_center(request):
    # Notifications (exclude chat message kind)
    notifs = (
        request.user.notifications
        .exclude(kind=Notification.Kind.MESSAGE)   # ⬅️ hide message-notifs
        .select_related("request", "request__item", "request__requester", "request__provider")
        .order_by("-created_at", "-id")
    )
    unread_notif_count = notifs.filter(is_read=False).count()

    # Conversations list (unchanged)
    convs = (
        Conversation.objects
        .filter(Q(user_a=request.user) | Q(user_b=request.user), is_active=True)
        .select_related("user_a", "user_b", "item")
        .order_by("-id")
    )

    conv_ids = list(convs.values_list("id", flat=True))
    last_rows = (
        Message.objects.filter(conversation_id__in=conv_ids)
        .values("conversation_id")
        .annotate(last_id=Max("id"))
    )
    last_id_map = {r["conversation_id"]: r["last_id"] for r in last_rows}
    last_msgs = {
        m.conversation_id: m
        for m in Message.objects.filter(pk__in=last_id_map.values()).select_related("sender")
    }

    for c in convs:
        lm = last_msgs.get(c.id)
        c.last = lm
        c.last_is_other = bool(lm and lm.sender_id != request.user.id)

    active_tab = request.GET.get("tab", "notifs")

    return render(
        request,
        "collab/notifications.html",
        {
            "notifs": notifs,
            "conversations": convs,
            "unread_notif_count": unread_notif_count,
            "active_tab": active_tab,
        },
    )


# @login_required
# def notifications_center(request):
#     notifs = (
#         request.user.notifications
#         .select_related("request")           # ← remove "message"
#         .order_by("-created_at", "-id")
#     )
#     return render(request, "collab/notifications.html", {"notifs": notifs})


@login_required
@require_POST
def notification_mark_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return JsonResponse({"ok": True})


# ----------------- Chat (HTTP polling) -----------------

def _ensure_participant(user, conversation):
    if user.id not in conversation.participants():
        raise Http404()

# collab/views.py

@login_required
def chat_view(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id, is_active=True)
    _ensure_participant(request.user, conv)

    # Make sure it's ordered by id, materialize to list, and compute last_id safely
    qs = conv.messages.select_related("sender").order_by("id")[:200]
    msgs = list(qs)
    last_id = msgs[-1].id if msgs else 0

    return render(
        request,
        "collab/chat.html",
        {
            "conv": conv,
            "messages": msgs,   # now a list, not a sliced queryset
            "last_id": last_id, # pass the last message id explicitly
        },
    )

# collab/views.py

@login_required
@require_POST
def chat_send(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id, is_active=True)
    _ensure_participant(request.user, conv)

    text = (request.POST.get("text") or "").strip()  # ← .strip(), not .trim()
    file = request.FILES.get("file")
    if not text and not file:
        return JsonResponse({"ok": False, "error": "Message empty."}, status=400)

    msg = Message.objects.create(conversation=conv, sender=request.user, text=text, file=file)

    # notifications disabled on purpose

    ts = timezone.localtime(msg.created_at).strftime("%H:%M")
    return JsonResponse({"ok": True, "id": msg.id, "ts": ts})


@login_required
@require_GET
def chat_poll(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id, is_active=True)
    _ensure_participant(request.user, conv)
    last_id = int(request.GET.get("after") or 0)
    qs = conv.messages.select_related("sender").filter(pk__gt=last_id).order_by("id")
    data = [{
        "id": m.id,
        "sender": m.sender.username,
        "me": (m.sender_id == request.user.id),
        "text": m.text,
        "file": (m.file.url if m.file else ""),
        "ts": m.created_at.strftime("%H:%M"),
    } for m in qs]
    return JsonResponse({"ok": True, "messages": data})



@login_required
def unread_count(request):
    count = request.user.notifications.filter(is_read=False).count()
    return JsonResponse({"count": count})