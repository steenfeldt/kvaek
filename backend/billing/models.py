from django.db import models

from accounts.storage import private_storage
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


class Invoice(models.Model):
    """Bookkeeping record: unbroken sequential numbering, seller and buyer
    snapshotted at issue time. Never deleted (payments are PROTECTed and GDPR
    erasure anonymizes around them)."""

    number = models.PositiveIntegerField(unique=True)
    payment = models.OneToOneField(Payment, on_delete=models.PROTECT, related_name="invoice")
    issued_at = models.DateTimeField(auto_now_add=True)

    seller_name = models.CharField(max_length=200)
    seller_cvr = models.CharField(max_length=8, blank=True)
    seller_address = models.CharField(max_length=300, blank=True)
    seller_email = models.EmailField(blank=True)

    buyer_company = models.CharField(max_length=200)
    buyer_cvr = models.CharField(max_length=8, blank=True)
    buyer_email = models.EmailField()

    description = models.CharField(max_length=300)
    net_ore = models.PositiveIntegerField()
    vat_ore = models.PositiveIntegerField()
    gross_ore = models.PositiveIntegerField()

    pdf = models.FileField(upload_to="invoices/%Y/", storage=private_storage, blank=True)

    def __str__(self):
        return f"Faktura {self.number}"
