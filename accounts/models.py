from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from core.utils.images import compress_image_field

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


    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_("کد کاربر (آرتونومی)"),
        help_text=_("مثال: artonomy-1, artonomy-2, ..."),
    )
    avatar = models.ImageField(
        upload_to=upload_to_profile,
        blank=True,
        null=True,
        verbose_name=_("عکس پروفایل"),
        help_text=_("تصویری که در کنار نام شما نمایش داده می‌شود."),
    )

    # ستون سمت چپ (header/column-image)
    header_background = models.ImageField(
        upload_to=upload_to_profile, blank=True, null=True,
        help_text=_("تصویر پس‌زمینه ستون سمت چپ (17.jpg فعلی)."))
    header_title = models.CharField(max_length=200, default="درباره من")
    header_subtitle = models.CharField(max_length=400, blank=True, default="")

    # داستان کوچک من
    story_title = models.CharField(max_length=200, default="داستان من")
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
        "story_paragraph_1",
        "avatar",   
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
    def missing_completion_items(self):
        """
        لیست بخش‌های ناقص پروفایل را برمی‌گرداند.
        هر آیتم یک tuple به شکل (tab_name, label) است.
        """
        items = []

        # ----- فیلدهای تب «پروفایل» -----
        if not self.avatar:
            items.append(("profile", "عکس پروفایل"))
        if not self.header_background:
            items.append(("profile", "تصویر هدر (کاور پروفایل)"))
        if not (self.header_subtitle or "").strip():
            items.append(("profile", "بایو کوتاه"))
        if not (self.story_paragraph_1 or "").strip():
            items.append(("profile", "داستان من - پاراگراف اول"))

        # ----- نقش / دسته‌بندی -----
        if self.role == "normal":
            items.append(("role", "انتخاب نقش (هنرمند / صاحب کسب‌وکار)"))
        elif self.role == "artist":
            if not self.category:
                items.append(("role", "انتخاب دسته هنری"))
            if not self.subcategory:
                items.append(("role", "انتخاب زیرشاخه هنری"))
        elif self.role == "business":
            if not self.business_kind:
                items.append(("role", "انتخاب نوع کسب‌وکار"))

        # ----- فرم‌ست‌ها -----
        if not self.counters.exists():
            items.append(("counters", "افزودن حداقل یک آمار (کارت ۴تایی)"))
        if not self.skills.exists():
            items.append(("skills", "افزودن حداقل یک مهارت"))
        # if not self.testimonials.exists():
        #     items.append(("testimonials", "افزودن حداقل یک نظر مشتری"))
        # if not self.clients.exists():
        #     items.append(("clients", "افزودن حداقل یک لوگوی مشتری"))

        return items
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

        # فقط این دو تا در درصد حساب بشن:
        # counters (15), skills (20)
        max_score += 15
        score += 15 if self.counters.exists() else 0

        max_score += 20
        score += 20 if self.skills.exists() else 0

        return min(100, round(score * 100 / max_score)) if max_score else 0


    def refresh_completion(self, save=True):
        new_val = self.compute_completion()
        if new_val != self.completion:
            self.completion = new_val
            if save:
                self.save(update_fields=["completion"])
        return self.completion
   
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
        # ✅ قبل از ذخیره، تصویر هدر و آواتار را فشرده کن
        if self.header_background:
            compress_image_field(self, "header_background", max_width=1920, quality=70)

        if self.avatar:
            # برای آواتار، رزولوشن کوچکتر
            compress_image_field(self, "avatar", max_width=600, quality=75)

        creating = self.pk is None
        super().save(*args, **kwargs)
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
    def save(self, *args, **kwargs):
        if self.background_image:
            compress_image_field(self, "background_image", max_width=1600, quality=70)
        super().save(*args, **kwargs)
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
    def save(self, *args, **kwargs):
        if self.image:
            compress_image_field(self, "image", max_width=600, quality=70)
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.profile.user.username} - {self.title or 'client'}"
