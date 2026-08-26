from datetime import datetime

from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from accounts.models import CreatorProfile

from . import services
from .models import TIER_CONFIG, Brief, Campaign, Deal, Proposal, Tier

router = Router(tags=["campaigns"], auth=django_auth)


def _brand_or_403(request):
    brand = getattr(request.user, "brand_profile", None)
    if brand is None:
        raise HttpError(403, "Brand account required")
    return brand


def _creator_or_403(request):
    creator = getattr(request.user, "creator_profile", None)
    if creator is None:
        raise HttpError(403, "Creator account required")
    return creator


def _domain(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except services.DomainError as e:
        raise HttpError(409, str(e))


class TierOut(Schema):
    tier: str
    price_ore: int
    briefs: int


@router.get("/tiers", response=list[TierOut], auth=None)
def tiers(request):
    return [TierOut(tier=t, **TIER_CONFIG[t]) for t in Tier.values]


class CampaignIn(Schema):
    name: str
    description: str = ""
    tier: str


class CampaignOut(Schema):
    id: int
    name: str
    description: str
    tier: str
    status: str
    briefs_total: int
    briefs_used: int
    created_at: datetime


@router.post("/campaigns", response=CampaignOut)
def create_campaign(request, payload: CampaignIn):
    brand = _brand_or_403(request)
    if payload.tier not in Tier.values:
        raise HttpError(422, "Unknown tier")
    return Campaign.objects.create(
        brand=brand, name=payload.name.strip(), description=payload.description.strip(), tier=payload.tier
    )


@router.get("/campaigns", response=list[CampaignOut])
def list_campaigns(request):
    brand = _brand_or_403(request)
    return brand.campaigns.all().order_by("-created_at")


class BriefIn(Schema):
    creator_id: int
    message: str


class BriefOut(Schema):
    id: int
    campaign_id: int
    creator_id: int
    creator_name: str
    campaign_name: str
    message: str
    status: str
    created_at: datetime


def _brief_out(b: Brief) -> BriefOut:
    return BriefOut(
        id=b.id,
        campaign_id=b.campaign_id,
        creator_id=b.creator_id,
        creator_name=b.creator.display_name,
        campaign_name=b.campaign.name,
        message=b.message,
        status=b.status,
        created_at=b.created_at,
    )


@router.post("/campaigns/{campaign_id}/briefs", response=BriefOut)
def send_brief(request, campaign_id: int, payload: BriefIn):
    brand = _brand_or_403(request)
    campaign = brand.campaigns.filter(id=campaign_id).first()
    if campaign is None:
        raise HttpError(404, "Campaign not found")
    creator = CreatorProfile.objects.filter(id=payload.creator_id).first()
    if creator is None:
        raise HttpError(404, "Creator not found")
    brief = _domain(services.send_brief, campaign, creator, payload.message.strip())
    return _brief_out(brief)


@router.get("/briefs", response=list[BriefOut])
def my_briefs(request):
    """Brand: briefs sent across campaigns. Creator: briefs received."""
    if getattr(request.user, "brand_profile", None):
        qs = Brief.objects.filter(campaign__brand=request.user.brand_profile)
    else:
        creator = _creator_or_403(request)
        qs = Brief.objects.filter(creator=creator)
    return [_brief_out(b) for b in qs.select_related("campaign", "creator").order_by("-created_at")]


class ProposalIn(Schema):
    amount_ore: int
    message: str = ""


class ProposalOut(Schema):
    id: int
    round: int
    author: str
    amount_ore: int
    message: str
    status: str
    created_at: datetime


def _get_brief_for_user(request, brief_id: int) -> tuple[Brief, str]:
    brief = Brief.objects.select_related("campaign__brand", "creator").filter(id=brief_id).first()
    if brief is None:
        raise HttpError(404, "Brief not found")
    if getattr(request.user, "brand_profile", None) == brief.campaign.brand:
        return brief, Proposal.Author.BRAND
    if getattr(request.user, "creator_profile", None) == brief.creator:
        return brief, Proposal.Author.CREATOR
    raise HttpError(404, "Brief not found")


@router.get("/briefs/{brief_id}/proposals", response=list[ProposalOut])
def list_proposals(request, brief_id: int):
    brief, _ = _get_brief_for_user(request, brief_id)
    return brief.proposals.all()


@router.post("/briefs/{brief_id}/proposals", response=ProposalOut)
def submit_proposal(request, brief_id: int, payload: ProposalIn):
    brief, side = _get_brief_for_user(request, brief_id)
    return _domain(services.submit_proposal, brief, side, payload.amount_ore, payload.message.strip())


@router.post("/briefs/{brief_id}/decline", response=BriefOut)
def decline_brief(request, brief_id: int):
    brief, _ = _get_brief_for_user(request, brief_id)
    return _brief_out(_domain(services.decline_brief, brief))


class DealOut(Schema):
    id: int
    brief_id: int
    agreed_amount_ore: int
    agreed_terms: str
    created_at: datetime
    completed: bool


@router.post("/briefs/{brief_id}/accept", response=DealOut)
def accept_proposal(request, brief_id: int):
    brief, side = _get_brief_for_user(request, brief_id)
    return _domain(services.accept_proposal, brief, side)


@router.get("/deals", response=list[DealOut])
def my_deals(request):
    if getattr(request.user, "brand_profile", None):
        deals = Deal.objects.filter(brief__campaign__brand=request.user.brand_profile)
    else:
        creator = _creator_or_403(request)
        deals = Deal.objects.filter(brief__creator=creator)
    return deals.order_by("-created_at")


@router.post("/deals/{deal_id}/complete", response=DealOut)
def complete_deal(request, deal_id: int):
    deal = Deal.objects.select_related("brief__campaign__brand", "brief__creator").filter(id=deal_id).first()
    if deal is None:
        raise HttpError(404, "Deal not found")
    if getattr(request.user, "brand_profile", None) == deal.brief.campaign.brand:
        side = "brand"
    elif getattr(request.user, "creator_profile", None) == deal.brief.creator:
        side = "creator"
    else:
        raise HttpError(404, "Deal not found")
    return _domain(services.mark_deal_completed, deal, side)
