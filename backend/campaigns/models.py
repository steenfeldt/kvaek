from django.db import models

from accounts.models import BrandProfile, CreatorProfile


class Tier(models.TextChoices):
    STARTER = "starter", "Starter"
    STANDARD = "standard", "Standard"
    REACH = "reach", "Reach"


# Price in øre (DKK, excl. VAT) and brief quota per tier.
TIER_CONFIG = {
    Tier.STARTER: {"price_ore": 299_00, "briefs": 5},
    Tier.STANDARD: {"price_ore": 799_00, "briefs": 20},
    Tier.REACH: {"price_ore": 1999_00, "briefs": 60},
}


class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tier = models.CharField(max_length=10, choices=Tier.choices)
    briefs_total = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    @property
    def briefs_used(self):
        return self.briefs.count()


class Brief(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        DECLINED = "declined", "Declined"
        NEGOTIATING = "negotiating", "Negotiating"
        ACCEPTED = "accepted", "Accepted"
        CLOSED = "closed", "Closed"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="briefs")
    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="briefs")
    message = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["campaign", "creator"], name="one_brief_per_creator_per_campaign"),
        ]


class Proposal(models.Model):
    class Author(models.TextChoices):
        CREATOR = "creator", "Creator"
        BRAND = "brand", "Brand"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        SUPERSEDED = "superseded", "Superseded"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    brief = models.ForeignKey(Brief, on_delete=models.CASCADE, related_name="proposals")
    round = models.PositiveSmallIntegerField()
    author = models.CharField(max_length=10, choices=Author.choices)
    amount_ore = models.PositiveIntegerField(help_text="Creator compensation in øre (off-platform in MVP)")
    message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["brief", "round"], name="one_proposal_per_round"),
        ]
        ordering = ["round"]


class Deal(models.Model):
    brief = models.OneToOneField(Brief, on_delete=models.CASCADE, related_name="deal")
    agreed_amount_ore = models.PositiveIntegerField()
    agreed_terms = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    brand_completed_at = models.DateTimeField(null=True, blank=True)
    creator_completed_at = models.DateTimeField(null=True, blank=True)

    @property
    def completed(self):
        return self.brand_completed_at is not None and self.creator_completed_at is not None
