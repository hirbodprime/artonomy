# core/models.py
from django.db import models

class HomepageAd(models.Model):
    POSITION_CHOICES = [
        (1, "اسلات 1"),
        (2, "اسلات 2"),
        (6, "اسلات 6"),
        (12, "اسلات 12"),
        (18, "اسلات 18"),
        (20, "اسلات 20"),
    ]

    title = models.CharField("عنوان", max_length=150,        blank=True,
        null=True)
    subtitle = models.CharField("زیرعنوان", max_length=250, blank=True)
    image = models.ImageField(
        "تصویر تبلیغ",
        upload_to="ads/homepage/",
        blank=True,
        null=True,
    )
    link_url = models.URLField("لینک مقصد", blank=True)
    button_label = models.CharField(
        "متن دکمه",
        max_length=50,
        blank=True,
        default="مشاهده",
    )

    position = models.PositiveSmallIntegerField(
        "جایگاه در صفحه",
        choices=POSITION_CHOICES,
        unique=True,
        help_text="مثلاً 1، 2، 6، 12، 18، 20",
    )

    is_active = models.BooleanField("فعال است؟", default=True)
    starts_at = models.DateTimeField("نمایش از", blank=True, null=True)
    ends_at = models.DateTimeField("نمایش تا", blank=True, null=True)

    bg_color = models.CharField(
        "رنگ پس‌زمینه",
        max_length=20,
        blank=True,
        help_text="مثلاً #111827 یا خالی برای پیش‌فرض",
    )
    text_color = models.CharField(
        "رنگ متن",
        max_length=20,
        blank=True,
        help_text="مثلاً #F9FAFB یا خالی برای پیش‌فرض",
    )

    class Meta:
        verbose_name = "تبلیغ صفحه اصلی"
        verbose_name_plural = "تبلیغ‌های صفحه اصلی"
        ordering = ["position"]

    def __str__(self):
        return f"{self.title} (اسلات {self.position})"

    @property
    def is_currently_visible(self):
        import datetime
        from django.utils import timezone

        if not self.is_active:
            return False
        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True
