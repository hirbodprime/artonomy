# marketplace/models.py
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.auth import get_user_model
User = get_user_model()
from core.utils.images import compress_image_field

CURRENCY_CHOICES = (
    ("IRT", "تومان"),
    ("IRR", "ریال"),
)

class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    class Meta:
        abstract = True

class Product(TimeStamped):
    class PriceType(models.TextChoices):
        FIXED = "fixed", _("قیمت ثابت")
        NEGOTIABLE = "neg", _("توافقی")

    class Condition(models.TextChoices):
        NEW = "new", _("نو")
        USED = "used", _("کارکرده")

    profile = models.ForeignKey("accounts.Profile", on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, blank=True)
    description = models.TextField(blank=True, default="")
    price_type = models.CharField(max_length=8, choices=PriceType.choices, default=PriceType.FIXED)
    price_amount = models.PositiveIntegerField(blank=True, null=True, help_text=_("برای قیمت ثابت پر شود"))
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="IRT")
    quantity = models.PositiveIntegerField(default=1)
    condition = models.CharField(max_length=8, choices=Condition.choices, default=Condition.NEW)
    # (optional legacy single image; safe to keep)
    image = models.ImageField(upload_to="market/products/%Y/%m/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-updated_at", "-id"]



    def display_price(self):
        if self.price_type == Product.PriceType.NEGOTIABLE:
            return "توافقی"
        if self.price_amount:
            unit = dict(CURRENCY_CHOICES).get(self.currency, "تومان")
            return f"{self.price_amount:,.0f} {unit}".replace(",", "٬")
        return "—"

    def get_absolute_url(self):
        return reverse("artpiece_detail", kwargs={"slug": self.slug, "pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True) or "item"

        # ✅ قبل از ذخیره، تصویر اصلی را هم فشرده کن
        if self.image:
            compress_image_field(self, "image", max_width=1600, quality=65)

        super().save(*args, **kwargs)

    @property
    def cover_image(self):
        # primary → lowest order → newest
        return self.images.order_by('-is_primary', 'order', 'id').first()

    def ordered_images(self):
        return self.images.order_by('-is_primary', 'order', 'id')
    @property
    def is_for_sale(self):
        return True

    def __str__(self):
        return self.title


class ProductImage(TimeStamped):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="market/products/%Y/%m/gallery/")
    alt_text = models.CharField(max_length=200, blank=True, default="")
    order = models.PositiveIntegerField(default=0, help_text=_("ترتیب نمایش"))
    is_primary = models.BooleanField(default=False, help_text=_("کاور/تصویر اصلی"))

    class Meta:
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        if self.image:
            # max_width را می‌توانی بسته به نیاز کمتر/بیشتر کنی
            compress_image_field(self, "image", max_width=1600, quality=65)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"تصویر {self.product_id} #{self.id}"



class Service(TimeStamped):
    class PricingModel(models.TextChoices):
        FIXED = "fixed", _("قیمت ثابت")
        RANGE = "range", _("بازه قیمتی")
        HOURLY = "hourly", _("ساعتی")
        QUOTE = "quote", _("براساس پروژه (استعلام)")

    profile = models.ForeignKey("accounts.Profile", on_delete=models.CASCADE, related_name="services")
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, blank=True)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="market/services/%Y/%m/", blank=True, null=True)  # legacy single
    tags = models.CharField(max_length=200, blank=True, default="", help_text=_("لیست برچسب‌ها با ویرگول"))
    pricing_model = models.CharField(max_length=10, choices=PricingModel.choices, default=PricingModel.QUOTE)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="IRT")
    min_price = models.PositiveIntegerField(blank=True, null=True)
    max_price = models.PositiveIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-updated_at", "-id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True)

        if self.image:
            compress_image_field(self, "image", max_width=1600, quality=65)

        super().save(*args, **kwargs)

    def display_price(self):
        unit = dict(CURRENCY_CHOICES).get(self.currency, "تومان")
        if self.pricing_model == Service.PricingModel.FIXED and self.min_price:
            return f"{self.min_price:,.0f} {unit}".replace(",", "٬")
        if self.pricing_model == Service.PricingModel.RANGE and self.min_price and self.max_price:
            lo = f"{self.min_price:,.0f}".replace(",", "٬")
            hi = f"{self.max_price:,.0f}".replace(",", "٬")
            return f"{lo}–{hi} {unit}"
        if self.pricing_model == Service.PricingModel.HOURLY and self.min_price:
            return f"{self.min_price:,.0f} {unit} / ساعت".replace(",", "٬")
        return "استعلام قیمت"

    def tag_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    # def cover_image(self):
    #     img = self.images.filter(is_primary=True).order_by("order", "id").first()
    #     if img: return img
    #     img = self.images.order_by("order", "id").first()
    #     return img

    def __str__(self):
        return self.title
    @property
    def cover_image(self):
        return self.images.order_by('-is_primary', 'order', 'id').first()
    def get_absolute_url(self):
        return reverse("service_detail", kwargs={"slug": self.slug, "pk": self.pk})

    def ordered_images(self):
        return self.images.order_by('-is_primary', 'order', 'id')


class ServiceImage(TimeStamped):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="market/services/%Y/%m/gallery/")
    alt_text = models.CharField(max_length=200, blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"تصویر سرویس {self.service_id} #{self.id}"

    def save(self, *args, **kwargs):
        if self.image:
            compress_image_field(self, "image", max_width=1600, quality=65)
        super().save(*args, **kwargs)




class ArtPost(TimeStamped):
    """
    محتوای هنری / پست بدون قیمت‌گذاری (فقط برای نمایش و جذب مخاطب)
    شبیه Product است ولی بدون قیمت.
    """
    class Condition(models.TextChoices):
        NEW = "new", _("نو")
        USED = "used", _("کارکرده")

    profile = models.ForeignKey(
        "accounts.Profile",
        on_delete=models.CASCADE,
        related_name="artposts",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, blank=True)
    description = models.TextField(blank=True, default="")
    quantity = models.PositiveIntegerField(default=1)  # اختیاری ولی شبیه Product
    condition = models.CharField(
        max_length=8,
        choices=Condition.choices,
        default=Condition.NEW,
    )
    image = models.ImageField(
        upload_to="market/artposts/%Y/%m/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    # ❤️‍🔥 تعاملات
    likes = models.ManyToManyField(
        User,
        related_name="liked_artposts",
        blank=True,
    )
    views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-updated_at", "-id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title, allow_unicode=True) or "post"

        if self.image:
            compress_image_field(self, "image", max_width=1600, quality=65)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    # شبیه Product ولی فقط برای نمایش
    def display_price(self):
        return "—"

    @property
    def is_for_sale(self):
        return False

    @property
    def cover_image(self):
        # primary → lowest order → newest
        img = self.images.order_by("-is_primary", "order", "id").first()
        if img:
            return img
        # fallback: legacy single image
        if self.image:
            # شبیه ProductImage interface (image.url)
            return None  # در تمپلیت خود image را چک می‌کنیم
        return None

    def ordered_images(self):
        return self.images.order_by("-is_primary", "order", "id")

    def get_absolute_url(self):
        return reverse("artpost_detail", kwargs={"slug": self.slug, "pk": self.pk})

    def total_likes(self):
        return self.likes.count()
    
    
class ArtPostImage(TimeStamped):
    artpost = models.ForeignKey(
        ArtPost,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="market/artposts/%Y/%m/gallery/")
    alt_text = models.CharField(max_length=200, blank=True, default="")
    order = models.PositiveIntegerField(default=0, help_text=_("ترتیب نمایش"))
    is_primary = models.BooleanField(default=False, help_text=_("کاور/تصویر اصلی"))

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"تصویر پست {self.artpost_id} #{self.id}"

    def save(self, *args, **kwargs):
        if self.image:
            compress_image_field(self, "image", max_width=1600, quality=65)
        super().save(*args, **kwargs)
