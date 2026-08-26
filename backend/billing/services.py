"""Mollie checkout + reconciliation + invoicing. The webhook (or return-page
poll) is the source of truth: we always fetch the payment from Mollie and
reconcile — never trust input. Tier prices are ex VAT; checkout charges gross
and a sequential invoice is issued the moment a payment becomes paid."""

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Max

from campaigns.models import TIER_CONFIG, Campaign
from campaigns.services import activate_campaign
from notifications import emails as notify

from .invoice_pdf import render_invoice_pdf
from .models import Invoice, Payment

VAT_RATE_PERCENT = 25


def vat_ore(net_ore: int) -> int:
    return net_ore * VAT_RATE_PERCENT // 100


def gross_ore(net_ore: int) -> int:
    return net_ore + vat_ore(net_ore)


def _client():
    from mollie.api.client import Client

    client = Client()
    client.set_api_key(settings.MOLLIE_API_KEY)
    return client


def create_checkout(campaign: Campaign) -> Payment:
    net = TIER_CONFIG[campaign.tier]["price_ore"]
    amount = gross_ore(net)
    payment = Payment.objects.create(campaign=campaign, amount_ore=amount)

    if not settings.MOLLIE_API_KEY:
        if not settings.DEBUG:
            raise RuntimeError("MOLLIE_API_KEY is not configured")
        # Dev fallback: no Mollie key — mark paid immediately so flows are testable.
        payment.status = Payment.Status.PAID
        payment.provider_snapshot = {"simulated": True}
        payment.save(update_fields=["status", "provider_snapshot", "updated_at"])
        activate_campaign(campaign)
        create_invoice(payment)
        return payment

    payload = {
        "amount": {"currency": "DKK", "value": f"{amount / 100:.2f}"},
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
        create_invoice(payment)
    return payment


def create_invoice(payment: Payment) -> Invoice:
    """Idempotent; sequential unbroken numbering (unique-constraint retry)."""
    existing = Invoice.objects.filter(payment=payment).first()
    if existing is not None:
        return existing
    campaign = payment.campaign
    brand = campaign.brand
    net = TIER_CONFIG[campaign.tier]["price_ore"]
    invoice = None
    for _ in range(5):
        number = (Invoice.objects.aggregate(m=Max("number"))["m"] or 0) + 1
        try:
            invoice = Invoice.objects.create(
                number=number,
                payment=payment,
                seller_name=settings.INVOICE_SELLER_NAME,
                seller_cvr=settings.INVOICE_SELLER_CVR,
                seller_address=settings.INVOICE_SELLER_ADDRESS,
                seller_email=settings.INVOICE_SELLER_EMAIL,
                buyer_company=brand.company_name,
                buyer_cvr=brand.cvr,
                buyer_email=brand.user.email,
                description=(
                    f'Kampagne "{campaign.name}" — {campaign.get_tier_display()}-pakke '
                    f"({TIER_CONFIG[campaign.tier]['briefs']} briefs)"
                ),
                net_ore=net,
                vat_ore=vat_ore(net),
                gross_ore=gross_ore(net),
            )
            break
        except IntegrityError:
            continue
    if invoice is None:
        raise RuntimeError("Could not allocate invoice number")
    pdf_bytes = render_invoice_pdf(invoice)
    invoice.pdf.save(f"faktura-{invoice.number}.pdf", ContentFile(pdf_bytes), save=True)
    notify.invoice_created(invoice, pdf_bytes)
    return invoice
