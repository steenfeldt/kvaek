from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["mollie_payment_id", "campaign", "amount_ore", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["provider_snapshot"]
