from django.http import FileResponse
from ninja import Form, Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from campaigns.models import Campaign

from . import services
from .models import Invoice

router = Router(tags=["billing"])


@router.get("/invoices/{invoice_id}/pdf", auth=django_auth)
def invoice_pdf(request, invoice_id: int):
    invoice = (
        Invoice.objects.select_related("payment__campaign__brand__user").filter(id=invoice_id).first()
    )
    if invoice is None or not invoice.pdf:
        raise HttpError(404, "Invoice not found")
    is_owner = invoice.payment.campaign.brand.user_id == request.user.id
    if not (is_owner or request.user.is_staff):
        raise HttpError(404, "Invoice not found")
    return FileResponse(
        invoice.pdf.open("rb"),
        as_attachment=True,
        filename=f"faktura-{invoice.number}.pdf",
        content_type="application/pdf",
    )


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
