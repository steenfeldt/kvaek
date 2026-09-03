from django.contrib.auth.models import AbstractUser, BaseUserManager
from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models

from .crypto import EncryptedTextField
from django.utils import timezone

from .storage import private_storage


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
    # Set when the user answers the first-login "want a password?" prompt with
    # "keep email codes" — once set, the prompt never comes back.
    password_prompt_dismissed_at = models.DateTimeField(null=True, blank=True)

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
    """Niches are curated: creators may suggest new ones, which stay private to
    the suggester until staff approve them."""

    MAX_PENDING_PER_USER = 3

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.APPROVED)
    suggested_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="suggested_niches"
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class City(models.Model):
    """Danish towns from DAWA (Dataforsyningen stednavne, type "by"), kept in
    sync by `manage.py sync_cities`. Names repeat across municipalities."""

    dawa_id = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=100, db_index=True)
    municipality = models.CharField(max_length=100)
    municipality_code = models.CharField(max_length=4)

    class Meta:
        ordering = ["name", "municipality"]
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name


class CreatorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="creator_profile")
    display_name = models.CharField(max_length=100)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    bio = models.TextField(blank=True)
    # Hashtags written in the bio (lowercased, without '#'), kept for search.
    bio_tags = ArrayField(models.CharField(max_length=30), default=list, blank=True)
    niches = models.ManyToManyField(NicheTag, blank=True, related_name="creators")
    # A creator appears in the swipe pool only when listed (completeness bar + moderation).
    listed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def city_name(self) -> str:
        return self.city.name if self.city else ""

    @property
    def verified(self) -> bool:
        """The profile badge: at least one channel with confirmed ownership."""
        return any(s.verified_at is not None for s in self.social_links.all())

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
    # Keep in sync with frontend/src/lib/platforms.ts (labels + icons live there).
    class Platform(models.TextChoices):
        INSTAGRAM = "instagram", "Instagram"
        TIKTOK = "tiktok", "TikTok"
        YOUTUBE = "youtube", "YouTube"
        FACEBOOK = "facebook", "Facebook"
        SNAPCHAT = "snapchat", "Snapchat"
        LINKEDIN = "linkedin", "LinkedIn"

    class VerificationMethod(models.TextChoices):
        NONE = "none", "Not verified"
        MANUAL = "manual", "Manual (screenshot reviewed by staff)"
        OAUTH = "oauth", "OAuth"  # Phase B

    # A verified channel with a live sync degrades to "stale" after this.
    STALE_AFTER = timedelta(days=3)
    MAX_SYNC_FAILURES = 3

    profile = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="social_links")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    # Re-resolved to the platform's canonical spelling on every sync. Never
    # shown to brands before a deal (anti-circumvention).
    handle = models.CharField(max_length=100)
    # The platform's stable account id, set on first successful lookup and
    # immutable after; unique per platform so one account can't back two profiles.
    external_id = models.CharField(max_length=100, null=True, blank=True)
    # Self-reported by the creator; live numbers live in ChannelMetricSnapshot.
    follower_count = models.PositiveIntegerField(default=0)
    verification_method = models.CharField(
        max_length=10, choices=VerificationMethod.choices, default=VerificationMethod.NONE
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_failures = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "platform"], name="unique_platform_per_profile"),
            models.UniqueConstraint(
                fields=["platform", "external_id"],
                condition=models.Q(external_id__isnull=False),
                name="unique_external_id_per_platform",
            ),
        ]

    def __str__(self):
        return f"{self.get_platform_display()} @{self.handle}"

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None

    @property
    def state(self) -> str:
        """Display state: verified | stale | unverified. Verification decays
        when the sync keeps failing or has gone quiet; it is never deleted."""
        if not self.is_verified:
            return "unverified"
        if self.sync_failures >= self.MAX_SYNC_FAILURES:
            return "stale"
        if self.last_sync_at and timezone.now() - self.last_sync_at > self.STALE_AFTER:
            return "stale"
        return "verified"

    def clear_verification(self) -> None:
        """A changed handle means a different account: drop ownership proof,
        the bound id and the failure counter. Snapshots stay as history."""
        self.verified_at = None
        self.verification_method = self.VerificationMethod.NONE
        self.external_id = None
        self.last_sync_at = None
        self.sync_failures = 0


class ChannelCredential(models.Model):
    """Phase B OAuth tokens — separate table so channel queries never touch
    secrets. Nothing writes here until a provider's OAuth flow is built."""

    channel = models.OneToOneField(SocialLink, on_delete=models.CASCADE, related_name="credential")
    access_token = EncryptedTextField()
    refresh_token = EncryptedTextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    scopes_granted = ArrayField(models.CharField(max_length=80), default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChannelMetricSnapshot(models.Model):
    """Append-only metrics per sync; gaps are as informative as values."""

    channel = models.ForeignKey(SocialLink, on_delete=models.CASCADE, related_name="snapshots")
    captured_at = models.DateTimeField(default=timezone.now)
    followers = models.BigIntegerField(null=True, blank=True)
    posts = models.BigIntegerField(null=True, blank=True)
    engagement_rate = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-captured_at"]
        constraints = [
            models.UniqueConstraint(fields=["channel", "captured_at"], name="one_snapshot_per_instant"),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("ChannelMetricSnapshot is append-only")
        super().save(*args, **kwargs)


class ProfilePhoto(models.Model):
    profile = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="creator_photos/%Y/%m/")
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]


class PortfolioItem(models.Model):
    """A past job the creator shows brands: one image or video plus text.
    Deliberately no link field — links carry handles (anti-circumvention)."""

    MAX_PER_PROFILE = 12

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    profile = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="portfolio")
    media = models.FileField(upload_to="portfolio/%Y/%m/")
    media_type = models.CharField(max_length=5, choices=MediaType.choices)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title


class BrandProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="brand_profile")
    company_name = models.CharField(max_length=200)
    # Required for new signups (validated at the API); blank only on
    # grandfathered/anonymized rows.
    cvr = models.CharField("CVR", max_length=8, blank=True)
    website = models.URLField(blank=True)
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def city_name(self) -> str:
        return self.city.name if self.city else ""

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cvr"], condition=~models.Q(cvr=""), name="unique_cvr_when_set"
            ),
        ]

    def __str__(self):
        return self.company_name


class VerificationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="verification_requests")
    # Ownership is proven per channel (a screenshot of that platform's insights).
    channel = models.ForeignKey(
        SocialLink, null=True, blank=True, on_delete=models.SET_NULL, related_name="verification_requests"
    )
    evidence = models.ImageField(upload_to="verification/%Y/%m/", storage=private_storage)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
