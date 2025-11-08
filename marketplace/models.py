# marketplace/models.py
from decimal import Decimal
from datetime import timedelta
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.db.models import Q, UniqueConstraint

from accounts.models import Category  # using your Category model

User = get_user_model()

# marketplace/models.py (add after Product model or wherever appropriate)
from django.conf import settings
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
        obj.refresh_from_db()
        return obj.join_clicks


class BusinessProfile(models.Model):
    """
    Public-facing 'studio' / 'artist page' / 'gallery page'.
    Moderation (is_approved) is separate from paywall (subscription_expires_at).
    Profile is LIVE only when both are satisfied.
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

    # Moderation gate
    is_approved = models.BooleanField(
        default=False,
        help_text=_("If not approved yet, profile is not shown publicly (even if subscribed).")
    )

    # Subscription / paywall gate
    trial_started_at = models.DateTimeField(null=True, blank=True)
    subscription_expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text=_("When this timestamp is in the past, the shop becomes hidden until renewed.")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_approved", "-created_at"]

    def __str__(self):
        return f"{self.display_name} ({self.get_kind_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.display_name) or "profile"
            candidate = base
            n = 1
            while BusinessProfile.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                n += 1
                candidate = f"{base}-{n}"
            self.slug = candidate
        super().save(*args, **kwargs)

    # ---- Subscription helpers ----
    def is_subscription_active(self) -> bool:
        """
        Returns True if now < subscription_expires_at.
        """
        if not self.subscription_expires_at:
            return False
        return timezone.now() < self.subscription_expires_at

    def is_live(self) -> bool:
        """
        A profile is LIVE when it is approved AND its subscription is active.
        """
        return bool(self.is_approved and self.is_subscription_active())

    def start_free_trial(self, days:int = 2, auto_approve:bool = True):
        """
        Start (or restart) a free trial now for `days`.
        Optionally auto-approve the profile so it is visible immediately.
        """
        now = timezone.now()
        self.trial_started_at = now
        self.subscription_expires_at = now + timedelta(days=days)
        if auto_approve:
            self.is_approved = True
        self.save(update_fields=["trial_started_at", "subscription_expires_at", "is_approved"])

    def extend_subscription(self, months:int = 1):
        """
        Extend subscription by `months` months from the *later* of now or current expiry.
        Use this after a successful monthly payment + admin approval.
        """
        now = timezone.now()
        base = self.subscription_expires_at if self.subscription_expires_at and self.subscription_expires_at > now else now
        # simple month = 30 days to avoid external libs; adjust if you want calendar months
        self.subscription_expires_at = base + timedelta(days=30 * months)
        # ensure it stays approved after renewal (moderation is separate but we keep this true)
        if not self.is_approved:
            self.is_approved = True
        self.save(update_fields=["subscription_expires_at", "is_approved"])
    def is_subscription_active(self) -> bool:
        if not self.subscription_expires_at:
            return False
        return timezone.now() < self.subscription_expires_at

    def is_on_trial(self) -> bool:
        """
        True iff the current expiry is within the initial trial window.
        """
        if not (self.trial_started_at and self.subscription_expires_at):
            return False
        return self.subscription_expires_at <= (self.trial_started_at + timedelta(days=2))

    def subscription_state(self) -> str:
        """
        Returns: "TRIAL", "ACTIVE", or "EXPIRED"
        """
        if not self.is_subscription_active():
            return "EXPIRED"
        return "TRIAL" if self.is_on_trial() else "ACTIVE"

    @property
    def public_products(self):
        return self.products.filter(status=Product.Status.ACTIVE).order_by("-views", "-id")[:8]


class JoinRequest(models.Model):
    """
    We keep JoinRequest as a thin audit of the onboarding attempt.
    Payment screenshot is no longer required by the new flow.
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
        default=Status.APPROVED,  # new flow: auto-approve on trial
    )

    # payment_image REMOVED from the new flow (not needed)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            UniqueConstraint(
                fields=["user", "profile"],
                condition=Q(status="PENDING"),
                name="uniq_pending_payment_per_user_profile",
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

# marketplace/models.py
from django.utils import timezone
from django.db import models
from decimal import Decimal

# marketplace/models.py (append near the bottom)

class SubscriptionPayment(models.Model):
    class Status(models.TextChoices):
        PENDING  = "PENDING",  _("Pending")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")

    profile = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name="subscription_payments",
    )
    # how much the user paid (optional display)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=12, default="TOMAN")

    # admin decides how many months to grant (default 1)
    months_granted = models.PositiveSmallIntegerField(default=1)

    # user proof
    payment_image = models.ImageField(upload_to="market/payments/", blank=True, null=True)

    # status
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    # audit
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_subscription_payments"
    )

    # snapshot of expiry change (filled when APPROVED)
    previous_expires_at = models.DateTimeField(null=True, blank=True)
    new_expires_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.profile.display_name} · {self.get_status_display()} · {self.created_at:%Y-%m-%d}"

    def approve(self, reviewer: User, months: int | None = None, note: str = ""):
        if self.status == self.Status.APPROVED:
            return

        if months and months > 0:
            self.months_granted = months

        now = timezone.now()
        self.previous_expires_at = self.profile.subscription_expires_at or now

        # extend profile
        self.profile.extend_subscription(months=self.months_granted)
        self.profile.trial_started_at = None
        self.profile.save(update_fields=["trial_started_at","subscription_expires_at","is_approved"])

        self.new_expires_at = self.profile.subscription_expires_at
        self.status = self.Status.APPROVED
        self.reviewed_at = now
        self.reviewed_by = reviewer
        if note:
            self.admin_note = (self.admin_note + "\n" if self.admin_note else "") + note

        self.save(update_fields=[
            "months_granted","previous_expires_at","new_expires_at",
            "status","reviewed_at","reviewed_by","admin_note",
        ])

    def reject(self, reviewer: User, note: str = ""):
        if self.status == self.Status.REJECTED:
            return
        self.status = self.Status.REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        if note:
            self.admin_note = note
        self.save(update_fields=["status", "reviewed_at", "reviewed_by", "admin_note"])
