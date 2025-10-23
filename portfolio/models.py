from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

# portfolio/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db import transaction

User = settings.AUTH_USER_MODEL

class PortfolioTheme(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    preview_image = models.ImageField(upload_to="themes/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    demo_url = models.URLField(blank=True, null=True)  # 👈 new field

    # NEW: monetization
    is_premium = models.BooleanField(default=False)
    price_cents = models.PositiveIntegerField(default=0, help_text="Price in cents (0 for free)")

    class Meta:
        ordering = ["name"]

    def __str__(self): return self.name

    @property
    def is_free(self) -> bool:
        return not self.is_premium or self.price_cents == 0


class ThemeLicense(models.Model):
    """
    Records that a user has purchased/unlocked a premium theme.
    No expiry by default; add expires_at if you want subscriptions.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="theme_licenses")
    theme = models.ForeignKey(PortfolioTheme, on_delete=models.CASCADE, related_name="licenses")
    purchased_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = [("user", "theme")]
        indexes = [models.Index(fields=["user", "theme"])]

    def __str__(self):
        return f"{self.user} → {self.theme} (licensed)"

    @property
    def is_active(self) -> bool:
        return self.expires_at is None or self.expires_at > timezone.now()


class UserPortfolio(models.Model):
    # NOTE: keep multi-portfolio support introduced earlier
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portfolio_sites")
    theme = models.ForeignKey(PortfolioTheme, on_delete=models.PROTECT, related_name="sites")
    title = models.CharField(max_length=120, blank=True)

    # Which portfolio is shown at @username/
    is_primary = models.BooleanField(default=False)

    # Can hide a specific site if needed
    is_published = models.BooleanField(default=True)

    # Legacy fields from previous step are harmless; optional to remove later
    plan = models.CharField(max_length=8, default="FREE")
    paid_until = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_primary=True),
                name="uniq_primary_portfolio_per_user",
            )
        ]
        ordering = ["-is_primary", "-updated_at"]

    def __str__(self):
        label = self.title or self.theme.name
        return f"{self.user} – {label}"

    @staticmethod
    def user_has_access(user, theme: PortfolioTheme) -> bool:
        """Free themes are open; premium themes require active license."""
        if theme.is_free:
            return True
        return ThemeLicense.objects.filter(user=user, theme=theme).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        ).exists()
    @classmethod
    def set_primary(cls, user, site_id):
        with transaction.atomic():
            qs = cls.objects.select_for_update().filter(user=user)
            site = qs.get(pk=site_id)
            # turn all off
            qs.update(is_primary=False)
            # turn the chosen one on
            site.is_primary = True
            site.save(update_fields=["is_primary", "updated_at"])
            return site

# ---------- Content owned by a user ----------

class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="portfolio_profile",        # was: "profile"
        related_query_name="portfolio_profile",  # add this to avoid E305
    )
    title = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    cover = models.ImageField(upload_to="covers/", blank=True, null=True)
    hero_image = models.ImageField(upload_to="heroes/", blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True)
    website = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=160, blank=True)
    email_public = models.EmailField(blank=True)

    def __str__(self):
        return f"Profile<{self.user}>"


class SocialLink(models.Model):
    KIND_CHOICES = [
        ("WEBSITE", "Website"), ("GITHUB", "GitHub"), ("X", "X/Twitter"),
        ("INSTAGRAM", "Instagram"), ("LINKEDIN", "LinkedIn"), ("OTHER", "Other"),
    ]
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="social_links")
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default="OTHER")
    label = models.CharField(max_length=80, blank=True)
    url = models.URLField()

    def __str__(self):
        return f"{self.profile.user} – {self.kind}"


class StatCounter(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="counters")
    icon = models.CharField(max_length=40, blank=True)  # e.g. "bi-emoji-smile"
    label = models.CharField(max_length=60)
    value = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["id"]


class Skill(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=60)
    percent = models.PositiveSmallIntegerField(default=50)  # 0..100

    class Meta:
        ordering = ["name"]


class Education(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="educations")
    school = models.CharField(max_length=160)
    degree = models.CharField(max_length=160, blank=True)
    start_year = models.CharField(max_length=12, blank=True)
    end_year = models.CharField(max_length=12, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]


class Experience(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="experiences")
    company = models.CharField(max_length=160)
    title = models.CharField(max_length=160)
    start_year = models.CharField(max_length=12, blank=True)
    end_year = models.CharField(max_length=12, blank=True)
    location = models.CharField(max_length=120, blank=True)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]


class Artwork(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="artworks")
    title = models.CharField(max_length=160)
    caption = models.TextField(blank=True)
    image = models.ImageField(upload_to="artworks/", blank=True, null=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return self.title


class ServiceItem(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="service_items")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, blank=True)  # "bi-briefcase"
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class Testimonial(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="testimonials")
    author_name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    text = models.TextField()
    photo = models.ImageField(upload_to="testimonials/", blank=True, null=True)

    class Meta:
        ordering = ["id"]
