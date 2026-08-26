import pytest
from django.contrib.auth import get_user_model

from accounts.models import BrandProfile
from billing import services
from billing.models import Invoice, Payment
from campaigns.models import Campaign, Tier

User = get_user_model()


@pytest.fixture
def brand(db):
    user = User.objects.create_user("faktura@example.com")
    return BrandProfile.objects.create(user=user, company_name="Faktura ApS", cvr="11111111")


def _paid_campaign(brand, name="C"):
    campaign = Campaign.objects.create(brand=brand, name=name, tier=Tier.STARTER)
    return services.create_checkout(campaign)  # dev simulation: pays + invoices


def test_checkout_charges_gross_with_vat(brand):
    payment = _paid_campaign(brand)
    assert payment.amount_ore == 37375  # 299,00 + 25% moms
    assert payment.status == Payment.Status.PAID


def test_invoice_created_with_correct_amounts(brand):
    payment = _paid_campaign(brand)
    invoice = payment.invoice
    assert invoice.net_ore == 29900
    assert invoice.vat_ore == 7475
    assert invoice.gross_ore == 37375
    assert invoice.buyer_company == "Faktura ApS"
    assert invoice.buyer_cvr == "11111111"
    assert f"faktura-{invoice.number}" in invoice.pdf.name
    assert invoice.pdf.size > 500


def test_invoice_numbers_are_sequential(brand):
    first = _paid_campaign(brand, "A").invoice
    second = _paid_campaign(brand, "B").invoice
    assert second.number == first.number + 1


def test_invoice_creation_is_idempotent(brand):
    payment = _paid_campaign(brand)
    again = services.create_invoice(payment)
    assert again.pk == payment.invoice.pk
    assert Invoice.objects.filter(payment=payment).count() == 1
