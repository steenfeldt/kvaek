from django.conf import settings
from django.db import models

from accounts.models import BrandProfile, CreatorProfile


class Shortlist(models.Model):
    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="shortlists")
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["brand", "name"], name="unique_shortlist_name_per_brand"),
        ]

    def __str__(self):
        return self.name


class ShortlistEntry(models.Model):
    shortlist = models.ForeignKey(Shortlist, on_delete=models.CASCADE, related_name="entries")
    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="shortlist_entries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["shortlist", "creator"], name="unique_creator_per_shortlist"),
        ]


class SwipeEvent(models.Model):
    class Direction(models.TextChoices):
        LIKE = "like", "Like"
        PASS = "pass", "Pass"

    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="swipes")
    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="swipes_received")
    direction = models.CharField(max_length=4, choices=Direction.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["brand", "creator", "-created_at"])]


class ProfileView(models.Model):
    brand = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name="profile_views")
    creator = models.ForeignKey(CreatorProfile, on_delete=models.CASCADE, related_name="profile_views")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["brand", "creator", "-created_at"])]
