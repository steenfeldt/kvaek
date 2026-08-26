"""All campaign/brief/proposal state transitions live here — nothing else mutates them."""

from django.db import transaction
from django.utils import timezone

from accounts.models import CreatorProfile
from notifications import emails as notify

from .models import TIER_CONFIG, Brief, Campaign, Deal, Proposal


class DomainError(Exception):
    """Raised for state-machine violations; maps to HTTP 409 at the API layer."""


@transaction.atomic
def activate_campaign(campaign: Campaign) -> Campaign:
    """Idempotent: called by both the Mollie webhook and the checkout return page."""
    campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
    if campaign.status == Campaign.Status.ACTIVE:
        return campaign
    if campaign.status != Campaign.Status.DRAFT:
        raise DomainError(f"Cannot activate a {campaign.status} campaign")
    campaign.status = Campaign.Status.ACTIVE
    campaign.briefs_total = TIER_CONFIG[campaign.tier]["briefs"]
    campaign.activated_at = timezone.now()
    campaign.save(update_fields=["status", "briefs_total", "activated_at"])
    return campaign


@transaction.atomic
def send_brief(campaign: Campaign, creator: CreatorProfile, message: str) -> Brief:
    campaign = Campaign.objects.select_for_update().get(pk=campaign.pk)
    if campaign.status != Campaign.Status.ACTIVE:
        raise DomainError("Campaign is not active")
    if campaign.briefs.count() >= campaign.briefs_total:
        raise DomainError("Brief quota for this campaign is used up")
    if campaign.briefs.filter(creator=creator).exists():
        raise DomainError("This creator already received a brief for this campaign")
    if not creator.listed:
        raise DomainError("Creator is not available")
    brief = Brief.objects.create(campaign=campaign, creator=creator, message=message)
    notify.brief_received(brief)
    return brief


@transaction.atomic
def decline_brief(brief: Brief) -> Brief:
    brief = Brief.objects.select_for_update().get(pk=brief.pk)
    if brief.status not in (Brief.Status.SENT, Brief.Status.NEGOTIATING):
        raise DomainError(f"Cannot decline a {brief.status} brief")
    brief.status = Brief.Status.DECLINED
    brief.save(update_fields=["status", "updated_at"])
    brief.proposals.filter(status=Proposal.Status.OPEN).update(status=Proposal.Status.DECLINED)
    return brief


# Bounded negotiation: round 1 creator, round 2 brand counter, round 3 creator final.
ROUND_AUTHOR = {1: Proposal.Author.CREATOR, 2: Proposal.Author.BRAND, 3: Proposal.Author.CREATOR}


@transaction.atomic
def submit_proposal(brief: Brief, author: str, amount_ore: int, message: str = "") -> Proposal:
    brief = Brief.objects.select_for_update().get(pk=brief.pk)
    if brief.status not in (Brief.Status.SENT, Brief.Status.NEGOTIATING):
        raise DomainError(f"Cannot propose on a {brief.status} brief")
    next_round = brief.proposals.count() + 1
    if next_round > Proposal.MAX_ROUNDS:
        raise DomainError("Negotiation is limited to three proposals")
    if ROUND_AUTHOR[next_round] != author:
        raise DomainError(f"Round {next_round} belongs to the {ROUND_AUTHOR[next_round]}")
    if amount_ore <= 0:
        raise DomainError("Amount must be positive")
    brief.proposals.filter(status=Proposal.Status.OPEN).update(status=Proposal.Status.SUPERSEDED)
    proposal = Proposal.objects.create(
        brief=brief, round=next_round, author=author, amount_ore=amount_ore, message=message
    )
    if brief.status != Brief.Status.NEGOTIATING:
        brief.status = Brief.Status.NEGOTIATING
        brief.save(update_fields=["status", "updated_at"])
    notify.proposal_received(proposal)
    return proposal


@transaction.atomic
def accept_proposal(brief: Brief, acting_side: str) -> Deal:
    """Either party may accept the other side's open proposal; that creates the deal."""
    brief = Brief.objects.select_for_update().get(pk=brief.pk)
    if brief.status != Brief.Status.NEGOTIATING:
        raise DomainError(f"Cannot accept on a {brief.status} brief")
    proposal = brief.proposals.filter(status=Proposal.Status.OPEN).first()
    if proposal is None:
        raise DomainError("No open proposal to accept")
    if proposal.author == acting_side:
        raise DomainError("Cannot accept your own proposal")
    proposal.status = Proposal.Status.ACCEPTED
    proposal.save(update_fields=["status"])
    brief.status = Brief.Status.ACCEPTED
    brief.save(update_fields=["status", "updated_at"])
    deal = Deal.objects.create(
        brief=brief, agreed_amount_ore=proposal.amount_ore, agreed_terms=proposal.message
    )
    notify.deal_created(deal)
    return deal


@transaction.atomic
def mark_deal_completed(deal: Deal, acting_side: str) -> Deal:
    deal = Deal.objects.select_for_update().get(pk=deal.pk)
    now = timezone.now()
    if acting_side == "brand" and deal.brand_completed_at is None:
        deal.brand_completed_at = now
        deal.save(update_fields=["brand_completed_at"])
    elif acting_side == "creator" and deal.creator_completed_at is None:
        deal.creator_completed_at = now
        deal.save(update_fields=["creator_completed_at"])
    return deal
