from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinLengthValidator
from django.contrib.postgres.fields import ArrayField  # optional; remove if not using Postgres

# from marketplace.models import MarketItem

User = settings.AUTH_USER_MODEL


class ServiceRequest(models.Model):
    class Status(models.TextChoices):
        PENDING_PROVIDER  = "PENDING_PROVIDER",  "Waiting for provider"
        ACCEPTED_PROVIDER = "ACCEPTED_PROVIDER", "Provider accepted (awaiting requester)"
        DECLINED          = "DECLINED",          "Declined"
        CANCELLED         = "CANCELLED",         "Cancelled"
        ACCEPTED_BOTH     = "ACCEPTED_BOTH",     "Accepted by both (chat open)"

    # item       = models.ForeignKey(MarketItem, on_delete=models.CASCADE, related_name="service_requests")
    requester  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_requests_made")
    provider   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_requests_received")
    brief      = models.TextField(validators=[MinLengthValidator(8)])
    attachments = models.FileField(upload_to="requests/attachments/", blank=True, null=True)
    status     = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING_PROVIDER)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Req #{self.pk} – {self.requester} → {self.provider} [{self.status}]"


class Conversation(models.Model):
    """Created automatically when both users accept."""
    # item      = models.ForeignKey(MarketItem, on_delete=models.CASCADE, related_name="conversations")
    request   = models.OneToOneField(ServiceRequest, on_delete=models.CASCADE, related_name="conversation")
    user_a    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_a")
    user_b    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_b")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def participants(self):
        return [self.user_a_id, self.user_b_id]

    def other(self, user):
        return self.user_b if user == self.user_a else self.user_a

    def __str__(self):
        return f"Chat #{self.pk} · {self.user_a} & {self.user_b} · item {self.item_id}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text         = models.TextField(blank=True)
    file         = models.FileField(upload_to="chat/files/", blank=True, null=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Msg {self.pk} by {self.sender_id} in chat {self.conversation_id}"


class Notification(models.Model):
    class Kind(models.TextChoices):
        REQUEST  = "REQUEST",  "Request"
        ACCEPT   = "ACCEPT",   "Accepted"
        CONFIRM  = "CONFIRM",  "Confirmed"
        MESSAGE  = "MESSAGE",  "Message"

    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    kind     = models.CharField(max_length=20, choices=Kind.choices, db_index=True)

    # ✅ make it safe to create without passing the flag every time
    is_read  = models.BooleanField(default=False, db_index=True)

    title    = models.CharField(max_length=180, blank=True)
    body     = models.TextField(blank=True)
    request  = models.ForeignKey("ServiceRequest", on_delete=models.CASCADE,
                                 null=True, blank=True, related_name="notifications")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
