from datetime import timedelta

from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from accounts.models import CreatorProfile

from .models import Shortlist, ShortlistEntry, SwipeEvent

router = Router(tags=["discovery"], auth=django_auth)

SEEN_GATE_DAYS = 30
DECK_SIZE = 20


def _brand_or_403(request):
    brand = getattr(request.user, "brand_profile", None)
    if brand is None:
        raise HttpError(403, "Brand account required")
    return brand


class SocialOut(Schema):
    platform: str
    follower_count: int
    verified: bool


class PortfolioOut(Schema):
    id: int
    media_type: str
    url: str
    title: str
    description: str


class DeckCardOut(Schema):
    id: int
    display_name: str
    city: str
    bio: str
    niches: list[str]
    verified: bool
    photo: str | None = None
    portfolio: list[PortfolioOut]
    socials: list[SocialOut]


def _card(profile: CreatorProfile) -> DeckCardOut:
    # Deliberately no handles / external links pre-deal (anti-circumvention).
    return DeckCardOut(
        id=profile.id,
        display_name=profile.display_name,
        city=profile.city_name,
        bio=profile.bio,
        niches=[t.name for t in profile.niches.all()],
        verified=profile.verified,
        photo=next((p.image.url for p in profile.photos.all()), None),
        portfolio=[
            PortfolioOut(
                id=i.id, media_type=i.media_type, url=i.media.url, title=i.title, description=i.description
            )
            for i in profile.portfolio.all()
        ],
        socials=[
            SocialOut(
                platform=s.platform,
                follower_count=s.follower_count,
                verified=s.verified_at is not None,
            )
            for s in profile.social_links.all()
        ],
    )


@router.get("/deck", response=list[DeckCardOut])
def deck(request, tag: str = ""):
    """The swipe pool, optionally narrowed to creators whose bio carries `#tag`."""
    brand = _brand_or_403(request)
    seen_since = timezone.now() - timedelta(days=SEEN_GATE_DAYS)
    seen_ids = SwipeEvent.objects.filter(brand=brand, created_at__gte=seen_since).values_list(
        "creator_id", flat=True
    )
    pool = CreatorProfile.objects.filter(listed=True).exclude(id__in=seen_ids)
    tag = tag.strip().lstrip("#").lower()
    if tag:
        pool = pool.filter(bio_tags__contains=[tag])
    profiles = pool.prefetch_related("niches", "photos", "portfolio", "social_links").order_by("?")[:DECK_SIZE]
    return [_card(p) for p in profiles]


class SwipeIn(Schema):
    creator_id: int
    direction: str


@router.post("/swipes")
def swipe(request, payload: SwipeIn):
    brand = _brand_or_403(request)
    if payload.direction not in SwipeEvent.Direction.values:
        raise HttpError(422, "direction must be 'like' or 'pass'")
    creator = CreatorProfile.objects.filter(id=payload.creator_id, listed=True).first()
    if creator is None:
        raise HttpError(404, "Creator not found")
    SwipeEvent.objects.create(brand=brand, creator=creator, direction=payload.direction)
    if payload.direction == SwipeEvent.Direction.LIKE:
        shortlist, _ = Shortlist.objects.get_or_create(brand=brand, name="Likes")
        ShortlistEntry.objects.get_or_create(shortlist=shortlist, creator=creator)
    return {"ok": True}


class ShortlistOut(Schema):
    id: int
    name: str
    count: int


@router.get("/shortlists", response=list[ShortlistOut])
def shortlists(request):
    brand = _brand_or_403(request)
    return [
        ShortlistOut(id=s.id, name=s.name, count=s.entries.count())
        for s in brand.shortlists.all().order_by("name")
    ]


@router.get("/shortlists/{shortlist_id}", response=list[DeckCardOut])
def shortlist_detail(request, shortlist_id: int):
    brand = _brand_or_403(request)
    shortlist = brand.shortlists.filter(id=shortlist_id).first()
    if shortlist is None:
        raise HttpError(404, "Shortlist not found")
    profiles = CreatorProfile.objects.filter(
        shortlist_entries__shortlist=shortlist, listed=True
    ).prefetch_related("niches", "photos", "portfolio", "social_links")
    return [_card(p) for p in profiles]


class SavedCountOut(Schema):
    saved_last_7_days: int


@router.get("/creator/saved-count", response=SavedCountOut)
def saved_count(request):
    # The creator-facing side of "silent shortlisting": aggregate only, never identities.
    creator = getattr(request.user, "creator_profile", None)
    if creator is None:
        raise HttpError(403, "Creator account required")
    since = timezone.now() - timedelta(days=7)
    count = ShortlistEntry.objects.filter(creator=creator, created_at__gte=since).count()
    return SavedCountOut(saved_last_7_days=count)
