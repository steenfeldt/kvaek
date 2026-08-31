from datetime import datetime

from django.db.models import Q
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
    price_incl_vat_ore: int
    briefs: int


@router.get("/tiers", response=list[TierOut], auth=None)
def tiers(request):
    from billing.services import gross_ore

    return [
        TierOut(tier=t, price_incl_vat_ore=gross_ore(TIER_CONFIG[t]["price_ore"]), **TIER_CONFIG[t])
        for t in Tier.values
    ]


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


class CampaignDetailOut(CampaignOut):
    briefs: list["BriefOut"]
    invoice_id: int | None = None
    invoice_number: int | None = None


@router.get("/campaigns/{campaign_id}", response=CampaignDetailOut)
def campaign_detail(request, campaign_id: int):
    brand = _brand_or_403(request)
    campaign = brand.campaigns.filter(id=campaign_id).first()
    if campaign is None:
        raise HttpError(404, "Campaign not found")
    if campaign.status == Campaign.Status.DRAFT:
        # Return-page polling path: reconcile any pending Mollie payment so the
        # campaign activates even if the webhook can't reach us (e.g. local dev).
        from billing.models import Payment
        from billing.services import reconcile_payment

        pending = campaign.payments.filter(
            status=Payment.Status.OPEN, mollie_payment_id__isnull=False
        )
        for payment in pending:
            reconcile_payment(payment.mollie_payment_id)
        campaign.refresh_from_db()
    from billing.models import Invoice

    invoice = Invoice.objects.filter(payment__campaign=campaign).first()
    briefs = campaign.briefs.select_related("campaign", "creator").order_by("-created_at")
    return CampaignDetailOut(
        invoice_id=invoice.id if invoice else None,
        invoice_number=invoice.number if invoice else None,
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        tier=campaign.tier,
        status=campaign.status,
        briefs_total=campaign.briefs_total,
        briefs_used=campaign.briefs_used,
        created_at=campaign.created_at,
        briefs=[_brief_out(b) for b in briefs],
    )


class BriefIn(Schema):
    creator_id: int
    message: str


class BriefOut(Schema):
    id: int
    campaign_id: int
    creator_id: int
    creator_name: str
    campaign_name: str
    brand_name: str
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
        brand_name=b.campaign.brand.company_name,
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


from .services import ROUND_AUTHOR


class BriefDetailOut(BriefOut):
    my_side: str
    proposals: list[ProposalOut]
    can_propose: bool
    can_accept: bool
    can_decline: bool
    deal_id: int | None = None


@router.get("/briefs/{brief_id}", response=BriefDetailOut)
def brief_detail(request, brief_id: int):
    brief, side = _get_brief_for_user(request, brief_id)
    proposals = list(brief.proposals.all())
    negotiable = brief.status in (Brief.Status.SENT, Brief.Status.NEGOTIATING)
    next_round = len(proposals) + 1
    open_proposal = next((p for p in proposals if p.status == Proposal.Status.OPEN), None)
    base = _brief_out(brief)
    return BriefDetailOut(
        **base.dict(),
        my_side=side,
        proposals=proposals,
        can_propose=negotiable and next_round <= Proposal.MAX_ROUNDS and ROUND_AUTHOR[next_round] == side,
        can_accept=brief.status == Brief.Status.NEGOTIATING
        and open_proposal is not None
        and open_proposal.author != side,
        can_decline=negotiable,
        deal_id=getattr(getattr(brief, "deal", None), "id", None),
    )


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
    campaign_name: str
    counterpart_name: str
    my_side: str
    agreed_amount_ore: int
    agreed_terms: str
    created_at: datetime
    completed: bool
    completed_by_me: bool
    completed_by_other: bool
    reviewed_by_me: bool


def _deal_side(deal: Deal, user) -> str:
    if getattr(user, "brand_profile", None) == deal.brief.campaign.brand:
        return "brand"
    if getattr(user, "creator_profile", None) == deal.brief.creator:
        return "creator"
    raise HttpError(404, "Deal not found")


def _deal_out(deal: Deal, user) -> DealOut:
    side = _deal_side(deal, user)
    if side == "brand":
        counterpart = deal.brief.creator.display_name
        mine, other = deal.brand_completed_at, deal.creator_completed_at
    else:
        counterpart = deal.brief.campaign.brand.company_name
        mine, other = deal.creator_completed_at, deal.brand_completed_at
    return DealOut(
        id=deal.id,
        brief_id=deal.brief_id,
        campaign_name=deal.brief.campaign.name,
        counterpart_name=counterpart,
        my_side=side,
        agreed_amount_ore=deal.agreed_amount_ore,
        agreed_terms=deal.agreed_terms,
        created_at=deal.created_at,
        completed=deal.completed,
        completed_by_me=mine is not None,
        completed_by_other=other is not None,
        reviewed_by_me=deal.reviews.filter(author=user).exists(),
    )


DEAL_RELATED = ("brief__campaign__brand", "brief__creator")


@router.post("/briefs/{brief_id}/accept", response=DealOut)
def accept_proposal(request, brief_id: int):
    brief, side = _get_brief_for_user(request, brief_id)
    deal = _domain(services.accept_proposal, brief, side)
    return _deal_out(Deal.objects.select_related(*DEAL_RELATED).get(pk=deal.pk), request.user)


@router.get("/deals", response=list[DealOut])
def my_deals(request):
    if getattr(request.user, "brand_profile", None):
        deals = Deal.objects.filter(brief__campaign__brand=request.user.brand_profile)
    else:
        creator = _creator_or_403(request)
        deals = Deal.objects.filter(brief__creator=creator)
    return [_deal_out(d, request.user) for d in deals.select_related(*DEAL_RELATED).order_by("-created_at")]


def _get_deal_for_user(request, deal_id: int) -> Deal:
    deal = Deal.objects.select_related(*DEAL_RELATED).filter(id=deal_id).first()
    if deal is None:
        raise HttpError(404, "Deal not found")
    _deal_side(deal, request.user)
    return deal


@router.get("/deals/{deal_id}", response=DealOut)
def deal_detail(request, deal_id: int):
    return _deal_out(_get_deal_for_user(request, deal_id), request.user)


@router.post("/deals/{deal_id}/complete", response=DealOut)
def complete_deal(request, deal_id: int):
    deal = _get_deal_for_user(request, deal_id)
    side = _deal_side(deal, request.user)
    _domain(services.mark_deal_completed, deal, side)
    deal.refresh_from_db()
    return _deal_out(deal, request.user)


class PoolCreatorOut(Schema):
    id: int
    display_name: str
    city: str
    photo: str | None = None


class BrandDashboardOut(Schema):
    company_name: str
    city: str
    waiting_proposals: int
    active_campaigns: int
    deals_in_flight: int
    pool_total: int
    pool_in_city: int
    new_in_pool: list[PoolCreatorOut]


@router.get("/dashboard/brand", response=BrandDashboardOut)
def brand_dashboard(request):
    brand = _brand_or_403(request)
    pool = CreatorProfile.objects.filter(listed=True)
    newest = pool.prefetch_related("photos").order_by("-created_at")[:4]
    return BrandDashboardOut(
        company_name=brand.company_name,
        city=brand.city,
        # Open creator proposals await the brand's answer.
        waiting_proposals=Proposal.objects.filter(
            brief__campaign__brand=brand,
            status=Proposal.Status.OPEN,
            author=Proposal.Author.CREATOR,
        ).count(),
        active_campaigns=brand.campaigns.filter(status=Campaign.Status.ACTIVE).count(),
        deals_in_flight=Deal.objects.filter(brief__campaign__brand=brand)
        .exclude(brand_completed_at__isnull=False, creator_completed_at__isnull=False)
        .count(),
        pool_total=pool.count(),
        pool_in_city=pool.filter(city__iexact=brand.city).count() if brand.city else 0,
        # Photo + name/city only — no handles or links pre-deal (anti-circumvention).
        new_in_pool=[
            PoolCreatorOut(
                id=p.id,
                display_name=p.display_name,
                city=p.city,
                photo=photos[0].image.url if (photos := list(p.photos.all())) else None,
            )
            for p in newest
        ],
    )


class CreatorDashboardOut(Schema):
    display_name: str
    city: str
    waiting_briefs: int
    deals_in_flight: int
    listed: bool
    profile_complete: bool


@router.get("/dashboard/creator", response=CreatorDashboardOut)
def creator_dashboard(request):
    creator = _creator_or_403(request)
    # A brief waits on the creator when it is unanswered, or the brand's
    # counter-proposal is the open one.
    waiting = (
        Brief.objects.filter(creator=creator)
        .filter(
            Q(status=Brief.Status.SENT)
            | Q(
                status=Brief.Status.NEGOTIATING,
                proposals__status=Proposal.Status.OPEN,
                proposals__author=Proposal.Author.BRAND,
            )
        )
        .distinct()
        .count()
    )
    return CreatorDashboardOut(
        display_name=creator.display_name,
        city=creator.city,
        waiting_briefs=waiting,
        deals_in_flight=Deal.objects.filter(brief__creator=creator)
        .exclude(brand_completed_at__isnull=False, creator_completed_at__isnull=False)
        .count(),
        listed=creator.listed,
        profile_complete=creator.meets_listing_bar(),
    )
