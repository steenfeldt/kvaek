import pytest
from django.contrib.auth import get_user_model

from accounts.models import BrandProfile, CreatorProfile
from campaigns import services
from campaigns.models import Brief, Campaign, Proposal, Tier
from campaigns.services import DomainError

User = get_user_model()


@pytest.fixture
def brand(db):
    user = User.objects.create_user("brand@example.com")
    return BrandProfile.objects.create(user=user, company_name="Café Test")


@pytest.fixture
def creator(db):
    user = User.objects.create_user("creator@example.com")
    return CreatorProfile.objects.create(user=user, display_name="Test Creator", listed=True)


@pytest.fixture
def active_campaign(brand):
    campaign = Campaign.objects.create(brand=brand, name="Summer", tier=Tier.STARTER)
    return services.activate_campaign(campaign)


def test_activation_is_idempotent(brand):
    campaign = Campaign.objects.create(brand=brand, name="C", tier=Tier.STANDARD)
    services.activate_campaign(campaign)
    services.activate_campaign(campaign)
    campaign.refresh_from_db()
    assert campaign.status == Campaign.Status.ACTIVE
    assert campaign.briefs_total == 20


def test_brief_quota_enforced(active_campaign, brand, db):
    assert active_campaign.briefs_total == 5
    for i in range(5):
        u = User.objects.create_user(f"c{i}@example.com")
        c = CreatorProfile.objects.create(user=u, display_name=f"C{i}", listed=True)
        services.send_brief(active_campaign, c, "hi")
    extra_user = User.objects.create_user("extra@example.com")
    extra = CreatorProfile.objects.create(user=extra_user, display_name="Extra", listed=True)
    with pytest.raises(DomainError, match="quota"):
        services.send_brief(active_campaign, extra, "hi")


def test_no_duplicate_brief_per_creator(active_campaign, creator):
    services.send_brief(active_campaign, creator, "hi")
    with pytest.raises(DomainError, match="already"):
        services.send_brief(active_campaign, creator, "hi again")


def test_no_briefs_on_draft_campaign(brand, creator):
    draft = Campaign.objects.create(brand=brand, name="Draft", tier=Tier.STARTER)
    with pytest.raises(DomainError, match="not active"):
        services.send_brief(draft, creator, "hi")


@pytest.fixture
def brief(active_campaign, creator):
    return services.send_brief(active_campaign, creator, "Interested?")


def test_negotiation_happy_path(brief):
    services.submit_proposal(brief, Proposal.Author.CREATOR, 150_000, "1500 kr for two posts")
    deal = services.accept_proposal(brief, Proposal.Author.BRAND)
    assert deal.agreed_amount_ore == 150_000
    brief.refresh_from_db()
    assert brief.status == Brief.Status.ACCEPTED


def test_negotiation_full_three_rounds(brief):
    services.submit_proposal(brief, Proposal.Author.CREATOR, 200_000)
    services.submit_proposal(brief, Proposal.Author.BRAND, 120_000)
    services.submit_proposal(brief, Proposal.Author.CREATOR, 150_000)
    with pytest.raises(DomainError, match="three"):
        services.submit_proposal(brief, Proposal.Author.BRAND, 140_000)
    deal = services.accept_proposal(brief, Proposal.Author.BRAND)
    assert deal.agreed_amount_ore == 150_000


def test_round_authorship_enforced(brief):
    with pytest.raises(DomainError, match="creator"):
        services.submit_proposal(brief, Proposal.Author.BRAND, 100_000)
    services.submit_proposal(brief, Proposal.Author.CREATOR, 100_000)
    with pytest.raises(DomainError, match="brand"):
        services.submit_proposal(brief, Proposal.Author.CREATOR, 90_000)


def test_cannot_accept_own_proposal(brief):
    services.submit_proposal(brief, Proposal.Author.CREATOR, 100_000)
    with pytest.raises(DomainError, match="own"):
        services.accept_proposal(brief, Proposal.Author.CREATOR)


def test_decline_ends_negotiation(brief):
    services.submit_proposal(brief, Proposal.Author.CREATOR, 100_000)
    services.decline_brief(brief)
    with pytest.raises(DomainError):
        services.submit_proposal(brief, Proposal.Author.BRAND, 90_000)
    with pytest.raises(DomainError):
        services.accept_proposal(brief, Proposal.Author.BRAND)


def test_deal_completion_needs_both_sides(brief):
    services.submit_proposal(brief, Proposal.Author.CREATOR, 100_000)
    deal = services.accept_proposal(brief, Proposal.Author.BRAND)
    services.mark_deal_completed(deal, "brand")
    assert not deal.completed
    services.mark_deal_completed(deal, "creator")
    deal.refresh_from_db()
    assert deal.completed


def test_brand_dashboard_counts(client, active_campaign, brand, creator):
    brief = services.send_brief(active_campaign, creator, "hi")
    services.submit_proposal(brief, Proposal.Author.CREATOR, 50000)
    client.force_login(brand.user)
    data = client.get("/api/dashboard/brand").json()
    assert data["company_name"] == "Café Test"
    assert data["waiting_proposals"] == 1
    assert data["active_campaigns"] == 1
    assert data["deals_in_flight"] == 0
    assert data["pool_total"] == 1
    assert [c["display_name"] for c in data["new_in_pool"]] == ["Test Creator"]

    # Accepting turns the open proposal into an in-flight deal.
    services.accept_proposal(brief, "brand")
    data = client.get("/api/dashboard/brand").json()
    assert data["waiting_proposals"] == 0
    assert data["deals_in_flight"] == 1
