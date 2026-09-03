from collections import Counter

from django.db import transaction
from django.db.models import Case, Count, IntegerField, Value, When
from django.db.models.functions import Length
from django.utils import timezone
from ninja import File, Router, Schema, UploadedFile
from ninja.errors import HttpError
from ninja.security import django_auth

from .models import (
    TERMS_VERSION,
    BrandProfile,
    City,
    CreatorProfile,
    NicheTag,
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
    since they belonged to the old account."""
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
    profile.social_links.exclude(platform__in=keep).delete()


def _hashtags_or_422(bio: str) -> list[str]:
    try:
        return extract_hashtags(bio)
    except ValueError as e:
        raise HttpError(422, str(e))


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
    for slug in payload.niches:
        tag = NicheTag.objects.filter(slug=slug).first()
        if tag:
            profile.niches.add(tag)
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


@router.get("/niches", response=list[NicheOut], auth=None)
def niches(request):
    return NicheTag.objects.all().order_by("name")


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
    photos: list[PhotoOut]


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
        niches=[NicheOut(name=t.name, slug=t.slug) for t in profile.niches.all()],
        social_links=[
            SocialLinkOut(
                platform=s.platform,
                handle=s.handle,
                follower_count=s.follower_count,
                verified=s.verified_at is not None,
            )
            for s in profile.social_links.all()
        ],
        photos=[PhotoOut(id=p.id, url=p.image.url) for p in profile.photos.all()],
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
        profile.niches.set(NicheTag.objects.filter(slug__in=payload.niches))
    if payload.social_links is not None:
        _sync_social_links(profile, payload.social_links)
    return _my_profile(profile)


MAX_PHOTOS = 6
MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@router.post("/me/photos", response=PhotoOut, auth=django_auth)
def upload_photo(request, file: File[UploadedFile]):
    profile = _creator_or_403(request)
    if profile.photos.count() >= MAX_PHOTOS:
        raise HttpError(409, f"Maximum {MAX_PHOTOS} photos")
    if file.size > MAX_UPLOAD_BYTES:
        raise HttpError(413, "File too large")
    try:
        image = process_profile_image(file)
    except Exception:
        raise HttpError(422, "Not a valid image")
    photo = ProfilePhoto.objects.create(
        profile=profile, image=image, sort_order=profile.photos.count()
    )
    return PhotoOut(id=photo.id, url=photo.image.url)


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

