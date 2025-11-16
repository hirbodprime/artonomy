from django.db import models
from django.utils import timezone
from django.conf import settings
from accounts.models import Profile

User = settings.AUTH_USER_MODEL


class SpotlightSettings(models.Model):
    star_name = models.CharField(max_length=50, default="ستاره")
    referral_reward = models.PositiveIntegerField(default=15) # stars for inviter
    invited_reward = models.PositiveIntegerField(default=5)   # stars for new user
    spotlight_cost = models.PositiveIntegerField(default=50)
    spotlight_hours = models.PositiveIntegerField(default=12)

    def __str__(self):
        return "تنظیمات سیستم اسپات‌لایت"

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class StarTransaction(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="star_logs")
    amount = models.IntegerField()   # + / -
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']


class Referral(models.Model):
    inviter = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="referrals_sent")
    invited = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="referral")
    created_at = models.DateTimeField(auto_now_add=True)
    rewarded = models.BooleanField(default=False)  # stars given?

    def __str__(self):
        return f"{self.inviter} invited {self.invited}"

    @property
    def invited_email(self):
        return getattr(self.invited.user, "email", "") if self.invited and self.invited.user_id else ""

    @property
    def invited_name(self):
        u = getattr(self.invited, "user", None)
        if not u:
            return ""
        return u.get_full_name() or u.username or u.email


class SpotlightBoost(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    expires_at = models.DateTimeField()

    @property
    def active(self):
        return timezone.now() < self.expires_at
