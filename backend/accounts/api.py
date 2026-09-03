import uuid
from collections import Counter

from django.core.files.base import ContentFile

from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.db.models.functions import Length
from django.utils import timezone
from django.utils.text import slugify
from ninja import File, Form, Router, Schema, UploadedFile
from ninja.errors import HttpError
from ninja.security import django_auth

from .models import (
    TERMS_VERSION,
    BrandProfile,
    City,
    CreatorProfile,
    NicheTag,
    PortfolioItem,
    ProfilePhoto,
    SocialLink,
    VerificationRequest,
)
from .services import extract_hashtags, process_profile_image

router = Router(tags=["accounts"])


class MeOut(Schema):
    authenticated: bool
    email: str | None = None
    role: str | None = None
    display_name: str | None = None
    is_staff: bool = False
    prompt_password_setup: bool = False


@router.get("/me", response=MeOut, auth=None)
def me(request):
    user = request.user
    if not user.is_authenticated:
        return MeOut(authenticated=False)
    role = user.role
    display_name = None
    if role == "creator":
        display_name = user.creator_profile.display_name
    elif role == "brand":
        display_name = user.brand_profile.company_name
    return MeOut(
        authenticated=True,
        email=user.email,
        role=role,
        display_name=display_name,
        is_staff=user.is_staff,
        # Offer a password only to code-only users (Google users don't need
        # one), and only until they set one or explicitly decline.
        prompt_password_setup=(
            not user.has_usable_password()
            and user.password_prompt_dismissed_at is None
            and not user.socialaccount_set.exists()
        ),
    )


@router.post("/me/password-prompt/dismiss", auth=django_auth)
def dismiss_password_prompt(request):
    """The user chose to keep email-code login — never ask again."""
    user = request.user
    if user.password_prompt_dismissed_at is None:
        user.password_prompt_dismissed_at = timezone.now()
        user.save(update_fields=["password_prompt_dismissed_at"])
    return {"ok": True}


class SocialLinkIn(Schema):
    platform: str
    handle: str
    follower_count: int = 0


class CreatorOnboardingIn(Schema):
    display_name: str
    city_id: int | None = None
    bio: str = ""
    niches: list[str] = []
    social_links: list[SocialLinkIn] = []
    accept_terms: bool = False


class BrandOnboardingIn(Schema):
    company_name: str
    cvr: str
    website: str = ""
    city_id: int | None = None
    accept_terms: bool = False


def _clean_cvr(cvr: str, exclude_profile_id: int | None = None) -> str:
    cvr = cvr.strip().replace(" ", "")
    if not (cvr.isdigit() and len(cvr) == 8):
        raise HttpError(422, "CVR must be 8 digits")
    qs = BrandProfile.objects.filter(cvr=cvr)
    if exclude_profile_id is not None:
        qs = qs.exclude(id=exclude_profile_id)
    if qs.exists():
        raise HttpError(409, "A brand with this CVR is already registered")
    return cvr


class OnboardingOut(Schema):
    role: str


def _city_or_422(city_id: int | None) -> City | None:
    if city_id is None:
        return None
    city = City.objects.filter(id=city_id).first()
    if city is None:
        raise HttpError(422, "Unknown city")
    return city


def _require_no_profile(user):
    if user.role is not None:
        raise HttpError(409, "Account already has a profile")


def _sync_social_links(profile: CreatorProfile, links: list[SocialLinkIn]) -> None:
    """Make the profile's channels match `links`: one per platform, an empty
    handle removes the channel. A changed handle drops any API-confirmed stats,
    since they belonged to the old account. At least one channel must remain —
    reach is the whole point of the card."""
    keep = []
    for link in links:
        handle = link.handle.strip().lstrip("@")
        if link.platform not in SocialLink.Platform.values or not handle:
            continue
        existing = profile.social_links.filter(platform=link.platform).first()
        if existing is None:
            existing = SocialLink(profile=profile, platform=link.platform)
        elif existing.handle != handle:
            existing.verified_at = None
        existing.handle = handle
        existing.follower_count = max(0, link.follower_count)
        existing.save()
        keep.append(link.platform)
    if not keep:
        raise HttpError(422, "Add at least one channel")
    profile.social_links.exclude(platform__in=keep).delete()


def _hashtags_or_422(bio: str) -> list[str]:
    try:
        return extract_hashtags(bio)
    except ValueError as e:
        raise HttpError(422, str(e))


def _usable_niches(user):
    """Approved niches, plus the user's own suggestions still under review."""
    return NicheTag.objects.filter(
        Q(status=NicheTag.Status.APPROVED) | Q(status=NicheTag.Status.PENDING, suggested_by=user)
    )


def _record_terms(user, accepted: bool):
    if not accepted:
        raise HttpError(422, "Terms must be accepted")
    user.terms_accepted_at = timezone.now()
    user.terms_version = TERMS_VERSION
    user.save(update_fields=["terms_accepted_at", "terms_version"])


@router.post("/onboarding/creator", response=OnboardingOut, auth=django_auth)
@transaction.atomic
def onboard_creator(request, payload: CreatorOnboardingIn):
    _require_no_profile(request.user)
    _record_terms(request.user, payload.accept_terms)
    profile = CreatorProfile.objects.create(
        user=request.user,
        display_name=payload.display_name.strip(),
        city=_city_or_422(payload.city_id),
        bio=payload.bio.strip(),
        bio_tags=_hashtags_or_422(payload.bio),
    )
    profile.niches.set(_usable_niches(request.user).filter(slug__in=payload.niches))
    _sync_social_links(profile, payload.social_links)
    return OnboardingOut(role="creator")


@router.post("/onboarding/brand", response=OnboardingOut, auth=django_auth)
@transaction.atomic
def onboard_brand(request, payload: BrandOnboardingIn):
    _require_no_profile(request.user)
    cvr = _clean_cvr(payload.cvr)
    _record_terms(request.user, payload.accept_terms)
    BrandProfile.objects.create(
        user=request.user,
        company_name=payload.company_name.strip(),
        cvr=cvr,
        website=payload.website.strip(),
        city=_city_or_422(payload.city_id),
    )
    return OnboardingOut(role="brand")


class MyBrandOut(Schema):
    company_name: str
    cvr: str
    website: str
    city: str
    city_id: int | None = None

    @staticmethod
    def resolve_city(obj) -> str:
        return obj.city_name


def _brand_or_403(request) -> BrandProfile:
    brand = getattr(request.user, "brand_profile", None)
    if brand is None:
        raise HttpError(403, "Brand account required")
    return brand


@router.get("/me/brand", response=MyBrandOut, auth=django_auth)
def my_brand(request):
    return _brand_or_403(request)


class BrandUpdateIn(Schema):
    company_name: str | None = None
    cvr: str | None = None
    website: str | None = None
    city_id: int | None = None


@router.patch("/me/brand", response=MyBrandOut, auth=django_auth)
def update_brand(request, payload: BrandUpdateIn):
    brand = _brand_or_403(request)
    if payload.cvr is not None:
        brand.cvr = _clean_cvr(payload.cvr, exclude_profile_id=brand.id)
    for field in ("company_name", "website"):
        value = getattr(payload, field)
        if value is not None:
            setattr(brand, field, value.strip())
    # null clears the city; an absent key leaves it alone.
    if "city_id" in payload.dict(exclude_unset=True):
        brand.city = _city_or_422(payload.city_id)
    if not brand.company_name:
        raise HttpError(422, "Company name is required")
    brand.save()
    return brand


class NicheOut(Schema):
    name: str
    slug: str
    # True for the caller's own suggestions awaiting review (hidden from others).
    pending: bool = False


def _niche_out(tag: NicheTag) -> NicheOut:
    return NicheOut(name=tag.name, slug=tag.slug, pending=tag.status == NicheTag.Status.PENDING)


@router.get("/niches", response=list[NicheOut], auth=None)
def niches(request):
    if request.user.is_authenticated:
        qs = _usable_niches(request.user)
    else:
        qs = NicheTag.objects.filter(status=NicheTag.Status.APPROVED)
    return [_niche_out(t) for t in qs.order_by("name")]


class NicheSuggestIn(Schema):
    name: str


@router.post("/niches/suggest", response=NicheOut, auth=django_auth)
def suggest_niche(request, payload: NicheSuggestIn):
    """Propose a new niche. It is usable by the suggester right away but only
    becomes public once staff approve it in admin."""
    name = " ".join(payload.name.split())
    if not 2 <= len(name) <= 50:
        raise HttpError(422, "Niche name must be 2-50 characters")
    name = name[0].upper() + name[1:]
    slug = slugify(name)
    if not slug:
        raise HttpError(422, "Niche name must contain letters or digits")
    existing = NicheTag.objects.filter(Q(slug=slug) | Q(name__iexact=name)).first()
    if existing is not None:
        if existing.status == NicheTag.Status.APPROVED:
            return _niche_out(existing)
        if existing.status == NicheTag.Status.PENDING and existing.suggested_by_id == request.user.id:
            return _niche_out(existing)
        if existing.status == NicheTag.Status.PENDING:
            raise HttpError(409, "This niche has already been suggested and is awaiting review")
        raise HttpError(422, "This niche was not accepted")
    pending = NicheTag.objects.filter(status=NicheTag.Status.PENDING, suggested_by=request.user).count()
    if pending >= NicheTag.MAX_PENDING_PER_USER:
        raise HttpError(409, f"You already have {NicheTag.MAX_PENDING_PER_USER} niches awaiting review")
    tag = NicheTag.objects.create(
        name=name, slug=slug, status=NicheTag.Status.PENDING, suggested_by=request.user
    )
    return _niche_out(tag)


class HashtagOut(Schema):
    tag: str
    count: int


@router.get("/hashtags", response=list[HashtagOut], auth=None)
def hashtags(request, q: str = "", limit: int = 8):
    """Hashtags in use across listed creators, most common first — feeds the
    `#` suggestion menu so spelling converges."""
    q = q.strip().lstrip("#").lower()
    limit = max(1, min(limit, 20))
    counts: Counter[str] = Counter()
    for tags in CreatorProfile.objects.filter(listed=True).values_list("bio_tags", flat=True):
        counts.update(t for t in tags if t.startswith(q))
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    return [HashtagOut(tag=t, count=n) for t, n in ranked]


class CityOut(Schema):
    id: int
    name: str
    municipality: str
    # Display text: the name, plus the municipality when the name is ambiguous.
    label: str


@router.get("/cities", response=list[CityOut], auth=None)
def cities(request, q: str = "", limit: int = 20):
    q = q.strip()
    if not q:
        return []
    limit = max(1, min(limit, 50))
    matches = list(
        City.objects.filter(name__istartswith=q)
        .annotate(
            exact=Case(When(name__iexact=q, then=Value(0)), default=Value(1), output_field=IntegerField()),
            name_len=Length("name"),
        )
        .order_by("exact", "name_len", "name", "municipality")[:limit]
    )
    counts = dict(
        City.objects.filter(name__in={c.name for c in matches})
        .values_list("name")
        .annotate(n=Count("id"))
    )
    return [
        CityOut(
            id=c.id,
            name=c.name,
            municipality=c.municipality,
            label=c.name if counts.get(c.name, 1) == 1 else f"{c.name} ({c.municipality})",
        )
        for c in matches
    ]


def _creator_or_403(request) -> CreatorProfile:
    creator = getattr(request.user, "creator_profile", None)
    if creator is None:
        raise HttpError(403, "Creator account required")
    return creator


class PhotoOut(Schema):
    id: int
    url: str


class SocialLinkOut(Schema):
    platform: str
    handle: str
    follower_count: int
    verified: bool


class PortfolioOut(Schema):
    id: int
    media_type: str
    url: str
    title: str
    description: str


def _portfolio_out(item: PortfolioItem) -> PortfolioOut:
    return PortfolioOut(
        id=item.id,
        media_type=item.media_type,
        url=item.media.url,
        title=item.title,
        description=item.description,
    )


class MyProfileOut(Schema):
    display_name: str
    city: str
    city_id: int | None = None
    bio: str
    bio_tags: list[str] = []
    listed: bool
    verified: bool
    verification_status: str | None = None
    niches: list[NicheOut]
    social_links: list[SocialLinkOut]
    photo: PhotoOut | None = None
    portfolio: list[PortfolioOut]


def _my_profile(profile: CreatorProfile) -> MyProfileOut:
    latest_verification = profile.verification_requests.order_by("-created_at").first()
    return MyProfileOut(
        display_name=profile.display_name,
        city=profile.city_name,
        city_id=profile.city_id,
        bio=profile.bio,
        bio_tags=profile.bio_tags,
        listed=profile.listed,
        verified=profile.verified,
        verification_status=latest_verification.status if latest_verification else None,
        niches=[_niche_out(t) for t in profile.niches.all() if t.status != NicheTag.Status.REJECTED],
        social_links=[
            SocialLinkOut(
                platform=s.platform,
                handle=s.handle,
                follower_count=s.follower_count,
                verified=s.verified_at is not None,
            )
            for s in profile.social_links.all()
        ],
        photo=next((PhotoOut(id=p.id, url=p.image.url) for p in profile.photos.all()), None),
        portfolio=[_portfolio_out(i) for i in profile.portfolio.all()],
    )


@router.get("/me/profile", response=MyProfileOut, auth=django_auth)
def my_profile(request):
    return _my_profile(_creator_or_403(request))


class ProfileUpdateIn(Schema):
    display_name: str | None = None
    city_id: int | None = None
    bio: str | None = None
    niches: list[str] | None = None
    social_links: list[SocialLinkIn] | None = None


@router.patch("/me/profile", response=MyProfileOut, auth=django_auth)
@transaction.atomic
def update_profile(request, payload: ProfileUpdateIn):
    profile = _creator_or_403(request)
    for field in ("display_name", "bio"):
        value = getattr(payload, field)
        if value is not None:
            setattr(profile, field, value.strip())
    if "city_id" in payload.dict(exclude_unset=True):
        profile.city = _city_or_422(payload.city_id)
    if payload.bio is not None:
        profile.bio_tags = _hashtags_or_422(profile.bio)
    if not profile.display_name:
        raise HttpError(422, "Name is required")
    profile.save()
    if payload.niches is not None:
        profile.niches.set(_usable_niches(request.user).filter(slug__in=payload.niches))
    if payload.social_links is not None:
        _sync_social_links(profile, payload.social_links)
    return _my_profile(profile)


MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
VIDEO_TYPES = {"mp4": "video/mp4", "webm": "video/webm", "mov": "video/quicktime"}


@router.post("/me/photos", response=PhotoOut, auth=django_auth)
@transaction.atomic
def upload_photo(request, file: File[UploadedFile]):
    """One profile photo: uploading again replaces the current one."""
    profile = _creator_or_403(request)
    if file.size > MAX_UPLOAD_BYTES:
        raise HttpError(413, "File too large")
    try:
        image = process_profile_image(file)
    except Exception:
        raise HttpError(422, "Not a valid image")
    for old in profile.photos.all():
        old.image.delete(save=False)
        old.delete()
    photo = ProfilePhoto.objects.create(profile=profile, image=image)
    return PhotoOut(id=photo.id, url=photo.image.url)


@router.post("/me/portfolio", response=PortfolioOut, auth=django_auth)
def add_portfolio_item(
    request, file: File[UploadedFile], title: str = Form(...), description: str = Form("")
):
    profile = _creator_or_403(request)
    if profile.portfolio.count() >= PortfolioItem.MAX_PER_PROFILE:
        raise HttpError(409, f"Maximum {PortfolioItem.MAX_PER_PROFILE} portfolio items")
    title = title.strip()
    if not title:
        raise HttpError(422, "Title is required")
    ext = (file.name or "").rsplit(".", 1)[-1].lower()
    if ext in VIDEO_TYPES or (file.content_type or "").startswith("video/"):
        if ext not in VIDEO_TYPES:
            raise HttpError(422, "Video must be MP4, WebM or MOV")
        if file.size > MAX_VIDEO_BYTES:
            raise HttpError(413, "Video too large (max 50 MB)")
        media = ContentFile(file.read(), name=f"{uuid.uuid4().hex}.{ext}")
        media_type = PortfolioItem.MediaType.VIDEO
    else:
        if file.size > MAX_UPLOAD_BYTES:
            raise HttpError(413, "File too large")
        try:
            media = process_profile_image(file, max_dimension=1600)
        except Exception:
            raise HttpError(422, "Not a valid image or video")
        media_type = PortfolioItem.MediaType.IMAGE
    item = PortfolioItem.objects.create(
        profile=profile,
        media=media,
        media_type=media_type,
        title=title[:100],
        description=description.strip(),
        sort_order=profile.portfolio.count(),
    )
    return _portfolio_out(item)


class PortfolioUpdateIn(Schema):
    title: str | None = None
    description: str | None = None


@router.patch("/me/portfolio/{int:item_id}", response=PortfolioOut, auth=django_auth)
def update_portfolio_item(request, item_id: int, payload: PortfolioUpdateIn):
    profile = _creator_or_403(request)
    item = profile.portfolio.filter(id=item_id).first()
    if item is None:
        raise HttpError(404, "Portfolio item not found")
    if payload.title is not None:
        if not payload.title.strip():
            raise HttpError(422, "Title is required")
        item.title = payload.title.strip()[:100]
    if payload.description is not None:
        item.description = payload.description.strip()
    item.save()
    return _portfolio_out(item)


class PortfolioOrderIn(Schema):
    ids: list[int]


@router.put("/me/portfolio/order", response=list[PortfolioOut], auth=django_auth)
@transaction.atomic
def reorder_portfolio(request, payload: PortfolioOrderIn):
    """Set the display order; `ids` must be exactly the creator's items."""
    profile = _creator_or_403(request)
    items = {i.id: i for i in profile.portfolio.all()}
    if sorted(payload.ids) != sorted(items):
        raise HttpError(422, "ids must list every portfolio item exactly once")
    for position, item_id in enumerate(payload.ids):
        items[item_id].sort_order = position
        items[item_id].save(update_fields=["sort_order"])
    return [_portfolio_out(i) for i in profile.portfolio.all()]


@router.delete("/me/portfolio/{int:item_id}", auth=django_auth)
def delete_portfolio_item(request, item_id: int):
    profile = _creator_or_403(request)
    item = profile.portfolio.filter(id=item_id).first()
    if item is None:
        raise HttpError(404, "Portfolio item not found")
    item.media.delete(save=False)
    item.delete()
    return {"ok": True}


@router.delete("/me/photos/{photo_id}", auth=django_auth)
def delete_photo(request, photo_id: int):
    profile = _creator_or_403(request)
    photo = profile.photos.filter(id=photo_id).first()
    if photo is None:
        raise HttpError(404, "Photo not found")
    photo.image.delete(save=False)
    photo.delete()
    return {"ok": True}


@router.post("/me/verification", auth=django_auth)
def request_verification(request, file: File[UploadedFile]):
    profile = _creator_or_403(request)
    if profile.verified:
        raise HttpError(409, "Already verified")
    if profile.verification_requests.filter(status=VerificationRequest.Status.PENDING).exists():
        raise HttpError(409, "A verification request is already pending")
    if file.size > MAX_UPLOAD_BYTES:
        raise HttpError(413, "File too large")
    try:
        # Larger cap than profile photos — screenshots must stay legible.
        evidence = process_profile_image(file, max_dimension=1600)
    except Exception:
        raise HttpError(422, "Not a valid image")
    VerificationRequest.objects.create(creator=profile, evidence=evidence)
    return {"status": "pending"}

