from django.contrib import admin

from .models import Brief, Campaign, Deal, Proposal


class BriefInline(admin.TabularInline):
    model = Brief
    extra = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "brand", "tier", "status", "briefs_total", "created_at"]
    list_filter = ["status", "tier"]
    inlines = [BriefInline]


class ProposalInline(admin.TabularInline):
    model = Proposal
    extra = 0


@admin.register(Brief)
class BriefAdmin(admin.ModelAdmin):
    list_display = ["campaign", "creator", "status", "created_at"]
    list_filter = ["status"]
    inlines = [ProposalInline]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ["brief", "agreed_amount_ore", "created_at", "brand_completed_at", "creator_completed_at"]
