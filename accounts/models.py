from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.core.validators import RegexValidator
import re
from django.utils.translation import get_language


username_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9_]+$',
    message=_("Username may only contain letters, numbers, and underscores."),
)
# -------------------------
# Core taxonomy / user
class Category(models.Model):
    """Neutral taxonomy for posts (no WORK/FAV here)."""
    # English (existing)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=96, unique=True, blank=True)

    # Persian (new)
    name_fa = models.CharField(_("Persian name"), max_length=80, blank=True, null=True)
    slug_fa = models.SlugField(
        _("Persian slug"),
        max_length=96,
        unique=True,
        blank=True,
        null=True,
        allow_unicode=True,   # lets you keep Persian chars in the slug
    )

    image = models.ImageField(
        upload_to="categories/",
        blank=True, null=True,
        help_text=_("Representative image for this category.")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        # Show localized label in admin etc., but keep .name as English
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        if self.name_fa and not self.slug_fa:
            # unicode slug for Persian
            self.slug_fa = slugify(self.name_fa, allow_unicode=True)
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        lang = (get_language() or "").lower()
        return self.name_fa or self.name if lang.startswith("fa") else self.name

    @property
    def display_slug(self) -> str:
        lang = (get_language() or "").lower()
        return (self.slug_fa or self.slug) if lang.startswith("fa") else self.slug


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)

        if not extra_fields.get("username"):
            base_username = email.split("@")[0]
            # strip invalid chars, keep only [a-zA-Z0-9_]
            base_username = re.sub(r'[^a-zA-Z0-9_]', '', base_username)
            extra_fields["username"] = base_username or "user"

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        extra_fields.setdefault("role", User.Role.ARTIST)
        return self._create_user(email, password, **extra_fields)

LANG_CHOICES = (("fa", "Persian"), ("en", "English"))

class User(AbstractUser):
    class Role(models.TextChoices):
        ARTIST = "ARTIST", _("Artist")
        AUDIENCE = "AUDIENCE", _("Audience")
    language = models.CharField(max_length=5, choices=LANG_CHOICES, default="fa")
    email_verified = models.BooleanField(default=False)

    email = models.EmailField(_("email address"), unique=True)
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        validators=[username_validator],
        help_text=_("Required. Letters, numbers, and underscores only."),
    )

    public_number = models.PositiveIntegerField(unique=True, null=True, blank=True, db_index=True)
    public_code   = models.CharField(max_length=24, unique=True, null=True, blank=True, db_index=True)  # e.g. "A-12345"

    role = models.CharField(
        max_length=8,
        choices=Role.choices,
        db_index=True,
        null=True,
        blank=True,
    )

    categories = models.ManyToManyField("Category", through="UserCategory", blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = UserManager()
    def formatted_public_code(self) -> str:
        # helper if you ever want zero-padding like A-00001
        return f"A-{self.public_number}" if self.public_number else ""

    def __str__(self) -> str:
        return f"{self.username} <{self.email}>"
class PublicNumberCounter(models.Model):
    """Singleton counter to allocate the next public number atomically."""
    name = models.CharField(max_length=32, unique=True, default="global")
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name}:{self.last_number}"


class UserCategory(models.Model):
    class Kind(models.TextChoices):
        WORK = "WORK", _("Work")
        FAV  = "FAV",  _("Favorite")

    user     = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    kind     = models.CharField(max_length=8, choices=Kind.choices)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "category", "kind")

    def __str__(self):
        return f"{self.user} – {self.category} [{self.kind}]"


# -------------------------
# Profile + “personal info”
# -------------------------
class SkillTag(models.Model):
    name = models.CharField(max_length=64, unique=True)
    class Meta: ordering = ["name"]
    def __str__(self): return self.name


class Profile(models.Model):
    user   = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    title  = models.CharField(max_length=120, blank=True)  # “Designer | Photographer”
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    cover  = models.ImageField(upload_to="covers/",  blank=True, null=True)
    phone  = models.CharField(max_length=32, blank=True)
    skills = models.ManyToManyField(SkillTag, blank=True, related_name="profiles")
    bio    = models.TextField(blank=True)

    def __str__(self): return f"Profile<{self.user}>"


class SocialLink(models.Model):
    class Kind(models.TextChoices):
        WEBSITE = "WEBSITE", _("Website")
        GITHUB  = "GITHUB",  _("GitHub")
        TWITTER = "TWITTER", _("Twitter/X")
        INSTAGRAM = "INSTAGRAM", _("Instagram")
        LINKEDIN = "LINKEDIN", _("LinkedIn")
        OTHER   = "OTHER",   _("Other")

    profile  = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="social_links")
    kind     = models.CharField(max_length=16, choices=Kind.choices, default=Kind.OTHER)
    label    = models.CharField(max_length=80, blank=True)  # shown text
    url      = models.URLField()

    class Meta: ordering = ["kind", "label"]
    def __str__(self): return f"{self.profile.user} – {self.kind}"


class PersonalValue(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="values")
    name    = models.CharField(max_length=80)
    class Meta: ordering = ["name"]
    def __str__(self): return self.name


class HobbyInterest(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="hobbies")
    name    = models.CharField(max_length=80)
    class Meta: ordering = ["name"]
    def __str__(self): return self.name


class Achievement(models.Model):
    profile     = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="achievements")
    title       = models.CharField(max_length=160)
    date        = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)

    class Meta: ordering = ["-date", "-id"]
    def __str__(self): return self.title


class Goal(models.Model):
    profile     = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="goals")
    title       = models.CharField(max_length=160)
    date        = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)

    class Meta: ordering = ["-date", "-id"]
    def __str__(self): return self.title


class FunFact(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="funfacts")
    text    = models.CharField(max_length=220)
    class Meta: ordering = ["-id"]
    def __str__(self): return self.text[:40]


# -------------------------
# Portfolio (resume-style)
# -------------------------
class DatedBase(models.Model):
    start_date = models.DateField(blank=True, null=True)
    end_date   = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @property
    def period_label(self) -> str:
        if self.start_date and (self.end_date or self.is_current):
            end = "Present" if self.is_current or not self.end_date else self.end_date.strftime("%b %Y")
            return f"{self.start_date.strftime('%b %Y')} – {end}"
        return ""


class Education(DatedBase):
    profile  = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="educations")
    school   = models.CharField(max_length=160)
    degree   = models.CharField(max_length=160, blank=True)
    location = models.CharField(max_length=120, blank=True)
    summary  = models.TextField(blank=True)

    class Meta: ordering = ["-is_current", "-end_date", "-start_date", "id"]
    def __str__(self): return self.school


class Experience(DatedBase):
    profile  = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="experiences")
    company  = models.CharField(max_length=160)
    title    = models.CharField(max_length=160)
    location = models.CharField(max_length=120, blank=True)
    summary  = models.TextField(blank=True)

    class Meta: ordering = ["-is_current", "-end_date", "-start_date", "id"]
    def __str__(self): return f"{self.title} @ {self.company}"


class Book(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="books")
    title   = models.CharField(max_length=160)
    author  = models.CharField(max_length=120, blank=True)
    year    = models.CharField(max_length=16, blank=True)
    note    = models.TextField(blank=True)
    class Meta: ordering = ["title"]
    def __str__(self): return self.title


class Certification(models.Model):
    profile       = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="certifications")
    name          = models.CharField(max_length=160)
    issuer        = models.CharField(max_length=160, blank=True)
    issue_date    = models.DateField(blank=True, null=True)
    credential_id = models.CharField(max_length=120, blank=True)
    url           = models.URLField(blank=True)
    class Meta: ordering = ["-issue_date", "name"]
    def __str__(self): return self.name


class Course(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="courses")
    name    = models.CharField(max_length=160)
    org     = models.CharField(max_length=160, blank=True)
    date    = models.DateField(blank=True, null=True)
    note    = models.TextField(blank=True)
    class Meta: ordering = ["-date", "name"]
    def __str__(self): return self.name


class Project(DatedBase):
    profile     = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="projects")
    title       = models.CharField(max_length=160)
    employer    = models.CharField(max_length=160, blank=True)  # company/client
    description = models.TextField(blank=True)
    tech_stack  = models.CharField(max_length=300, blank=True)  # comma-separated
    url         = models.URLField(blank=True)

    class Meta: ordering = ["-is_current", "-end_date", "-start_date", "id"]
    def __str__(self): return self.title

    @property
    def tech_list(self):
        return [s.strip() for s in (self.tech_stack or "").split(",") if s.strip()]


class Award(models.Model):
    profile      = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="awards")
    title        = models.CharField(max_length=200)
    organization = models.CharField(max_length=200, blank=True)
    date         = models.DateField(blank=True, null=True)
    description  = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return self.title





from django.utils import timezone
from django.conf import settings
import secrets
from datetime import timedelta

class EmailOTP(models.Model):
    class Purpose(models.TextChoices):
        VERIFY_EMAIL   = "VERIFY_EMAIL", "Verify Email"
        RESET_PASSWORD = "RESET_PASSWORD", "Reset Password"

    user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_otps")
    email    = models.EmailField()
    purpose  = models.CharField(max_length=20, choices=Purpose.choices)
    code     = models.CharField(max_length=6, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts   = models.PositiveSmallIntegerField(default=0)
    is_used    = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["email", "purpose", "code"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} [{self.purpose}] {self.code} {'(used)' if self.is_used else ''}"

    @classmethod
    def create_code(cls, user, email, purpose, ttl_minutes=15):
        code = f"{secrets.randbelow(1000000):06d}"
        return cls.objects.create(
            user=user,
            email=email,
            purpose=purpose,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )

    def is_valid(self, submitted):
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        if self.code != submitted:
            return False
        return True
