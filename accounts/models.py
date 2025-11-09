from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

User = get_user_model()

PROFILE_CODE_PREFIX = "artonomy-"

def upload_to_profile(instance, filename):
    return f"profiles/{instance.user_id}/{filename}"

def upload_to_profile_misc(instance, filename):
    return f"profiles/{instance.profile.user_id}/misc/{filename}"

BUSINESS_KINDS = (
    ("gallery", "گالری"),
    ("studio", "استودیو"),
    ("concept_store", "کانسپت استور"),
)
class Profile(models.Model):
    ROLE_CHOICES = [
        ("normal", _("کاربر عادی")),
        ("artist", _("هنرمند")),
        ("business", _("صاخب کسب و کار")),
    ]
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True, null=True, blank=True)
    TRIAL_DAYS = 7

    trial_started_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("شروع دوره آزمایشی ۷ روزه")
    )
    subscription_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("تاریخ پایان اشتراک پولی (۱ دلاری در ماه)")
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_("کد کاربر (آرتونومی)"),
        help_text=_("مثال: artonomy-1, artonomy-2, ..."),
    )
    # ستون سمت چپ (header/column-image)
    header_background = models.ImageField(
        upload_to=upload_to_profile, blank=True, null=True,
        help_text=_("تصویر پس‌زمینه ستون سمت چپ (17.jpg فعلی)."))
    header_title = models.CharField(max_length=200, default="درباره من")
    header_subtitle = models.CharField(max_length=400, blank=True, default="")

    # داستان کوچک من
    story_title = models.CharField(max_length=200, default="داستان کوچک من")
    story_subtitle = models.CharField(max_length=400, blank=True, default="")
    story_paragraph_1 = models.TextField(blank=True, default="")
    story_paragraph_2 = models.TextField(blank=True, default="")

    # نقش کاربر
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="normal")
    category     = models.ForeignKey("artists.Category", null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="profiles")
    subcategory  = models.ForeignKey("artists.Subcategory", null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="profiles")
    custom_subcategory = models.CharField(
        "زیرشاخه دلخواه",
        max_length=120,
        blank=True,
        default="",
    )

    business_kind = models.CharField(max_length=20, choices=BUSINESS_KINDS, blank=True, default="")

    # مهارت‌ها در سکشن بعدی و کانترها و ... به مدل‌های جدا وصل می‌شوند
    # لینک‌های اجتماعی در مدل SocialLink
    # مشتریان و نظرات در مدل Testimonial
    # لوگوهای مشتریان (clients) در مدل ClientLogo
    completion = models.PositiveSmallIntegerField(default=0, editable=False, db_index=True)


    # fields that count toward completion
    COMPLETION_FIELDS = (
        "header_background",
        "header_subtitle",
        "story_subtitle",
        "story_paragraph_1",
        "story_paragraph_2",
        # social links and counts will be added by view (see below)
    )

    def clean(self):
        # consistency between role and fields
        from django.core.exceptions import ValidationError
        if self.role == "artist":
            if not self.category:
                raise ValidationError({"category": "دسته‌بندی هنری را انتخاب کنید."})
            if not self.subcategory:
                raise ValidationError({"subcategory": "زیرشاخه مرتبط را انتخاب کنید."})
            # ensure subcategory belongs to selected category
            if self.subcategory and self.category and self.subcategory.category_id != self.category_id:
                raise ValidationError({"subcategory": "این زیرشاخه متعلق به دسته انتخاب‌شده نیست."})

        if self.role == "business":
            if not self.business_kind:
                raise ValidationError({"business_kind": "نوع کسب‌وکار را انتخاب کنید."})
            # business role does not require artist categories
            # (optional) clear them:
            # self.category = None
            # self.subcategory = None

    def compute_completion(self) -> int:
        score = 0
        max_score = 0

        # Basic text/image fields (10 each)
        for f in self.COMPLETION_FIELDS:
            max_score += 10
            val = getattr(self, f, None)
            if val:
                score += 10 if (not isinstance(val, str) or val.strip()) else 0

        # role + role-specific (20 total)
        max_score += 20
        role_pts = 0
        if self.role in {"artist", "business"}:
            role_pts += 10
            if self.role == "artist":
                if self.category and self.subcategory:
                    role_pts += 10
            elif self.role == "business":
                if self.business_kind:
                    role_pts += 10
        score += role_pts

        # counters (15), skills (20), testimonials (15), clients (15)
        max_score += 15; score += 15 if self.counters.exists() else 0
        max_score += 20; score += 20 if self.skills.exists() else 0
        max_score += 15; score += 15 if self.testimonials.exists() else 0
        max_score += 15; score += 15 if self.clients.exists() else 0

        return min(100, round(score * 100 / max_score)) if max_score else 0

    def refresh_completion(self, save=True):
        new_val = self.compute_completion()
        if new_val != self.completion:
            self.completion = new_val
            if save:
                self.save(update_fields=["completion"])
        return self.completion
    def ensure_trial_default(self, save=True):
        """
        Call this once when user hits dashboard for the first time.
        If the user has neither trial nor paid subscription, start 7-day trial.
        """
        if self.trial_started_at is None and self.subscription_expires_at is None:
            now = timezone.now()
            self.trial_started_at = now
            if save:
                self.save(update_fields=["trial_started_at"])

    @property
    def trial_ends_at(self):
        if not self.trial_started_at:
            return None
        return self.trial_started_at + timedelta(days=self.TRIAL_DAYS)

    @property
    def in_trial(self) -> bool:
        """True while 7-day trial is active."""
        end = self.trial_ends_at
        if not end:
            return False
        return timezone.now() <= end and not self.has_subscription

    @property
    def has_subscription(self) -> bool:
        """True if user has active paid subscription."""
        if not self.subscription_expires_at:
            return False
        return timezone.now() <= self.subscription_expires_at

    @property
    def can_use_premium(self) -> bool:
        """Can use products/services tabs."""
        return self.in_trial or self.has_subscription

    @property
    def premium_days_left(self) -> int:
        """
        How many days left from either trial or paid subscription.
        (rounds up; e.g. 0.4 day → 1)
        """
        # Paid subscription has priority
        target = None
        if self.has_subscription:
            target = self.subscription_expires_at
        elif self.trial_ends_at:
            target = self.trial_ends_at

        if not target:
            return 0

        delta = target - timezone.now()
        days = delta.days
        if delta.seconds > 0:
            days += 1
        return max(0, days)

    @property
    def subscription_status_label(self) -> str:
        if self.has_subscription:
            return "اشتراک ماهانه فعال"
        if self.in_trial:
            return "دوره آزمایشی ۷ روزه"
        return "بدون اشتراک"

    @property
    def is_trial_expired(self) -> bool:
        return (self.trial_ends_at is not None and
                timezone.now() > self.trial_ends_at and
                not self.has_subscription)
    @staticmethod
    def premium_q():
        """Return Q for active paid sub OR active 7-day trial."""
        now = timezone.now()
        trial_cutoff = now - timedelta(days=Profile.TRIAL_DAYS)
        return (
            Q(subscription_expires_at__gte=now)
            | Q(
                subscription_expires_at__isnull=True,
                trial_started_at__gte=trial_cutoff,
            )
        )
    def generate_code(self) -> str:
        """
        تولید کد ثابت بر اساس id پروفایل.
        مثال: art-1, art-2, ...
        """
        if not self.pk:
            return None
        from .models import PROFILE_CODE_PREFIX  # اگر بالا global گذاشتی، لازم نیست این خط
        return f"{PROFILE_CODE_PREFIX}{self.pk}"

    def ensure_code(self, save=True) -> str:
        """
        اگر پروفایل کد ندارد، آن را تولید و ذخیره می‌کند.
        """
        if self.code:
            return self.code
        if not self.pk:
            # هنوز در دیتابیس ذخیره نشده، بعد از save اصلی دوباره صدا زده می‌شود
            return None
        self.code = self.generate_code()
        if save:
            self.save(update_fields=["code"])
        return self.code

    def save(self, *args, **kwargs):
        # تشخیص اینکه این اولین بار ذخیره می‌شود یا نه
        creating = self.pk is None
        super().save(*args, **kwargs)
        # بعد از ذخیره‌ی اولیه، اگر کد نداریم، بر اساس pk تولید کن
        if creating and not self.code:
            self.code = self.generate_code()
            super(Profile, self).save(update_fields=["code"])

    def __str__(self):
        if self.code:
            return f"{self.code} ({self.user.username})"
        return f"Profile({self.user.username})"

    def get_absolute_url(self):
        return reverse("public_profile", args=[self.user.username])


class ProfileCounter(models.Model):
    """برای چهار آمارِ صفحه (پروژه‌های تمام شده، مشتریان خوشحال، ساعات کاری …)"""
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="counters")
    label = models.CharField(max_length=100)
    value = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.profile.user.username} - {self.label}: {self.value}"


class Skill(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=100)
    percent = models.PositiveIntegerField(default=0, help_text=_("0..100"))
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.profile.user.username} - {self.name} ({self.percent}%)"


class Testimonial(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="testimonials")
    person_name = models.CharField(max_length=100)
    quote = models.TextField()
    source_label = models.CharField(max_length=100, blank=True, default="")  # مثلاً "از طریق توییتر"
    source_url = models.URLField(blank=True, default="")
    background_image = models.ImageField(upload_to=upload_to_profile_misc, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.profile.user.username} - {self.person_name}"


class SocialLink(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="social_links")
    title = models.CharField(max_length=50)  # فیسبوک، اینستاگرام، ...
    url = models.URLField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.profile.user.username} - {self.title}"


class ClientLogo(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="clients")
    title = models.CharField(max_length=100, blank=True, default="")
    url = models.URLField(blank=True, default="")
    image = models.ImageField(upload_to=upload_to_profile_misc)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.profile.user.username} - {self.title or 'client'}"
