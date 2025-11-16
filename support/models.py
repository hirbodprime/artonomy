from django.conf import settings
from django.db import models

from accounts.models import Profile

class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ("open", "باز"),
        ("answered", "پاسخ داده شده"),
        ("closed", "بسته شده"),
    ]

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )

    subject = models.CharField("موضوع", max_length=200)
    message = models.TextField("توضیح مشکل / درخواست")
    status = models.CharField(
        "وضعیت",
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
    )
    admin_reply = models.TextField(
        "پاسخ پشتیبانی",
        blank=True,
    )

    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین بروزرسانی", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "تیکت پشتیبانی"
        verbose_name_plural = "تیکت‌های پشتیبانی"

    def __str__(self):
        return f"{self.subject} ({self.get_status_display()})"
