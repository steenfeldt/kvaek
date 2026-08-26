from django.conf import settings
from django.db import models

from campaigns.models import Deal


class Message(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["deal", "created_at"])]


class Review(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_written")
    rating = models.PositiveSmallIntegerField()
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["deal", "author"], name="one_review_per_party_per_deal"),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="rating_1_to_5"),
        ]
