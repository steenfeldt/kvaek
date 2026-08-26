from ninja import Form, Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from campaigns.models import Campaign

from . import services

router = Router(tags=["billing"])


class CheckoutOut(Schema):
    payment_id: int
    status: str
    checkout_url: str
    campaign_status: str


@router.post("/campaigns/{campaign_id}/checkout", response=CheckoutOut, auth=django_auth)
def checkout(request, campaign_id: int):
    brand = getattr(request.user, "brand_profile", None)
    if brand is None:
        raise HttpError(403, "Brand account required")
    campaign = brand.campaigns.filter(id=campaign_id).first()
    if campaign is None:
        raise HttpError(404, "Campaign not found")
    if campaign.status != Campaign.Status.DRAFT:
        raise HttpError(409, "Campaign is not awaiting payment")
    payment = services.create_checkout(campaign)
    campaign.refresh_from_db()
    return CheckoutOut(
        payment_id=payment.id,
        status=payment.status,
        checkout_url=payment.checkout_url,
        campaign_status=campaign.status,
    )


@router.post("/webhooks/mollie", auth=None)
def mollie_webhook(request, id: Form[str]):
    # Mollie posts only the payment id; we fetch and reconcile. Always 200 so
    # Mollie doesn't retry forever on unknown ids.
    services.reconcile_payment(id)
    return {"ok": True}
