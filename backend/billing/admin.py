from django.contrib import admin
from django.utils.html import format_html

from .models import Invoice, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["number", "buyer_company", "gross_ore", "issued_at", "pdf_link"]
    exclude = ["pdf"]
    readonly_fields = ["pdf_link"]

    @admin.display(description="PDF")
    def pdf_link(self, obj):
        if not obj.pdf:
            return "-"
        return format_html('<a href="/api/invoices/{}/pdf" target="_blank">faktura-{}.pdf</a>', obj.pk, obj.number)

    def has_delete_permission(self, request, obj=None):
        return False  # unbroken numbering: invoices are never deleted


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["mollie_payment_id", "campaign", "amount_ore", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["provider_snapshot"]
