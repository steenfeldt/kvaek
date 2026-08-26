from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra_fields)
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
        return self._create_user(email, password, **extra_fields)


# Bump when the legal documents change; acceptance is recorded per version.
TERMS_VERSION = "2026-08-26-draft"


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    terms_version = models.CharField(max_length=32, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def role(self):
        if hasattr(self, "creator_profile"):
            return "creator"
        if hasattr(self, "brand_profile"):
            return "brand"
        return None

    def __str__(self):
        return self.email


class NicheTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class InviteCode(models.Model):
    code = models.CharField(max_length=32, unique=True)
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)
    used_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="invite_codes_used"
    )
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class WaitlistEntry(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    handle = models.CharField(max_length=120, blank=True, help_text="Instagram/TikTok handle")
    created_at = models.DateTimeField(auto_now_add=True)
    invited_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.email


class CreatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="creator_profile")
    display_name = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    niches = models.ManyToManyField(NicheTag, blank=True, related_name="creators")
    # A creator appears in the swipe pool only when listed (completeness bar + moderation).
    listed = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    def meets_listing_bar(self):
        return bool(
            self.display_name
            and self.photos.exists()
            and self.social_links.exists()
            and self.niches.exists()
        )


class SocialLink(models.Model):
    class Platform(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        TIKTOK = "tiktok", "TikTok"

    profile = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="social_links")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    handle = models.CharField(max_length=100)
    # Self-reported until platform OAuth lands; verified_at marks API-confirmed stats.
    follower_count = models.PositiveIntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "platform"], name="unique_platform_per_profile"),
        ]

    def __str__(self):
        return f"{self.get_platform_display()} @{self.handle}"


class ProfilePhoto(models.Model):
    profile = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="creator_photos/%Y/%m/")
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]


class BrandProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="brand_profile")
    company_name = models.CharField(max_length=200)
    cvr = models.CharField("CVR", max_length=8, blank=True)
    website = models.URLField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name


class VerificationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="verification_requests")
    evidence = models.ImageField(upload_to="verification/%Y/%m/")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
