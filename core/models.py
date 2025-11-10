# core/models.py
import uuid
from django.db import models
from django.conf import settings

class Visit(models.Model):
    visitor_id   = models.CharField(max_length=64, db_index=True)  # از روی کوکی
    path         = models.CharField(max_length=500)
    referrer     = models.CharField(max_length=500, blank=True)
    utm_source   = models.CharField(max_length=100, blank=True)
    utm_medium   = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)

    ip_address   = models.GenericIPAddressField(null=True, blank=True)  # ✅ IP
    user_agent   = models.CharField(max_length=300, blank=True)         # (اختیاری ولی خوبه)

    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["utm_source", "utm_medium"]),
        ]

    def __str__(self):
        return f"{self.path} @ {self.created_at:%Y-%m-%d %H:%M}"
