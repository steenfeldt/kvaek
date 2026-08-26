from django.db import models

from campaigns.models import Campaign


class Payment(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"

    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name="payments")
    mollie_payment_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    amount_ore = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="DKK")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    checkout_url = models.URLField(blank=True)
    # Raw last-known Mollie payment object, for audit/debugging.
    provider_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.mollie_payment_id or 'pending'} ({self.status})"
