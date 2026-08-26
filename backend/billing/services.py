"""Mollie checkout + reconciliation. The webhook (or return-page poll) is the source
of truth: we always fetch the payment from Mollie and reconcile — never trust input."""

from django.conf import settings
from django.db import transaction

from campaigns.models import TIER_CONFIG, Campaign
from campaigns.services import activate_campaign

from .models import Payment


def _client():
    from mollie.api.client import Client

    client = Client()
    client.set_api_key(settings.MOLLIE_API_KEY)
    return client


def create_checkout(campaign: Campaign) -> Payment:
    price_ore = TIER_CONFIG[campaign.tier]["price_ore"]
    payment = Payment.objects.create(campaign=campaign, amount_ore=price_ore)

    if not settings.MOLLIE_API_KEY:
        if not settings.DEBUG:
            raise RuntimeError("MOLLIE_API_KEY is not configured")
        # Dev fallback: no Mollie key — mark paid immediately so flows are testable.
        payment.status = Payment.Status.PAID
        payment.provider_snapshot = {"simulated": True}
        payment.save(update_fields=["status", "provider_snapshot", "updated_at"])
        activate_campaign(campaign)
        return payment

    payload = {
        "amount": {"currency": "DKK", "value": f"{price_ore / 100:.2f}"},
        "description": f"Campaign: {campaign.name} ({campaign.get_tier_display()})",
        "redirectUrl": f"{settings.FRONTEND_URL}/campaigns/{campaign.id}/payment-return",
        "metadata": {"payment_id": payment.id, "campaign_id": campaign.id},
    }
    # Mollie requires a publicly reachable webhook URL; on localhost we rely on
    # the return page's reconcile-on-poll instead.
    if "localhost" not in settings.BACKEND_URL and "127.0.0.1" not in settings.BACKEND_URL:
        payload["webhookUrl"] = f"{settings.BACKEND_URL}/api/webhooks/mollie"
    mollie_payment = _client().payments.create(payload)
    payment.mollie_payment_id = mollie_payment.id
    payment.checkout_url = mollie_payment.checkout_url
    payment.save(update_fields=["mollie_payment_id", "checkout_url", "updated_at"])
    return payment


MOLLIE_STATUS_MAP = {
    "paid": Payment.Status.PAID,
    "failed": Payment.Status.FAILED,
    "canceled": Payment.Status.CANCELED,
    "expired": Payment.Status.EXPIRED,
}


@transaction.atomic
def reconcile_payment(mollie_payment_id: str) -> Payment | None:
    payment = Payment.objects.select_for_update().filter(mollie_payment_id=mollie_payment_id).first()
    if payment is None:
        return None
    mollie_payment = _client().payments.get(mollie_payment_id)
    payment.status = MOLLIE_STATUS_MAP.get(mollie_payment.status, Payment.Status.OPEN)
    payment.provider_snapshot = dict(mollie_payment)
    payment.save(update_fields=["status", "provider_snapshot", "updated_at"])
    if payment.status == Payment.Status.PAID:
        activate_campaign(payment.campaign)
    return payment
