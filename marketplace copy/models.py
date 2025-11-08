# marketplace/models.py
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify

from accounts.models import Category  # using your Category model

User = get_user_model()


class MarketplaceStats(models.Model):
    """
    Tracks global marketplace stats like how many people clicked 'Join'.
    This is basically a singleton row.
    """
    name = models.CharField(max_length=32, unique=True, default="global")
    join_clicks = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} clicks={self.join_clicks}"

    @classmethod
    def bump_join_clicks(cls):
        obj, _ = cls.objects.get_or_create(name="global")
        obj.join_clicks = models.F("join_clicks") + 1
        obj.save(update_fields=["join_clicks"])
        # refresh to get real int after F()
        obj.refresh_from_db()
        return obj.join_clicks


class BusinessProfile(models.Model):
    """
    Public-facing 'studio' / 'artist page' / 'gallery page'.
    This is what the world sees.
    """
    class Kind(models.TextChoices):
        SOLO_ARTIST   = "SOLO_ARTIST", _("Solo Artist")
        GALLERY       = "GALLERY",     _("Gallery")
        STUDIO        = "STUDIO",      _("Studio")
        CONCEPT_STORE = "CONCEPT_STORE", _("Concept Store")
        OTHER         = "OTHER",       _("Other / Creative Business")

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="business_profiles",
    )

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
    )

    display_name = models.CharField(
        max_length=200,
        help_text=_("Public name. For solo artists, usually your artist name.")
    )

    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        help_text=_("Auto-generated from display name. Used in URLs."),
    )

    tagline = models.CharField(
        max_length=240,
        blank=True,
        help_text=_("Short punchline. Example: 'Brutalist ceramic forms with Persian soul.'")
    )

    bio_long = models.TextField(
        blank=True,
        help_text=_(
            "Tell your story in a dramatic, emotional way. "
            "Who are you, why do you exist, what makes you different?"
        )
    )

    location = models.CharField(
        max_length=160,
        blank=True,
        help_text=_("City / Country or where you're based.")
    )

    avatar = models.ImageField(
        upload_to="market/profile/avatar/",
        blank=True,
        null=True,
        help_text=_("Logo or portrait.")
    )

    cover = models.ImageField(
        upload_to="market/profile/cover/",
        blank=True,
        null=True,
        help_text=_("Header / vibe image.")
    )

    is_approved = models.BooleanField(
        default=False,
        help_text=_("If not approved yet, profile is not shown publicly.")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_approved", "-created_at"]

    def __str__(self):
        return f"{self.display_name} ({self.get_kind_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.display_name) or "profile"
            # ensure uniqueness
            candidate = base
            n = 1
            while BusinessProfile.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def public_products(self):
        return self.products.filter(status=Product.Status.ACTIVE).order_by("-views", "-id")[:8]

from django.db.models import Q, UniqueConstraint

class JoinRequest(models.Model):
    """
    One per account at a time (normally).
    Tracks onboarding & payment proof.
    """
    class Status(models.TextChoices):
        PENDING  = "PENDING",  _("Pending Review")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="market_join_requests"
    )

    profile = models.OneToOneField(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="join_request"
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # payment screenshot
    payment_image = models.ImageField(
        upload_to="market/payments/",
        blank=True,
        null=True,
        help_text=_("Upload your bank transfer receipt / payment screenshot.")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # at most one PENDING per user
            UniqueConstraint(
                fields=["user"],
                condition=Q(status="PENDING"),
                name="uniq_pending_join_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user} -> {self.profile} [{self.status}]"


class Product(models.Model):
    """
    Items offered by a BusinessProfile:
    - physical artworks
    - services
    - design packages
    etc.
    """
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", _("Active")
        DRAFT  = "DRAFT",  _("Draft")
        SOLD   = "SOLD",   _("Sold")

    profile = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="products"
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # category of the product (art type / service domain)
    category = models.ForeignKey(
        Category,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="products"
    )

    # pricing
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )
    currency = models.CharField(
        max_length=12,
        default="TOMAN"
    )

    is_service = models.BooleanField(
        default=False,
        help_text=_("True = service (logo design, tattoo session, etc.). False = physical work.")
    )

    image = models.ImageField(
        upload_to="market/products/",
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    views = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.title} · {self.profile.display_name}"

    @property
    def can_buy(self):
        # disabled for now
        return False
