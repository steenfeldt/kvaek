from django.db import transaction
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja.security import django_auth

from .models import BrandProfile, CreatorProfile, InviteCode, NicheTag, SocialLink

router = Router(tags=["accounts"])


class MeOut(Schema):
    authenticated: bool
    email: str | None = None
    role: str | None = None
    display_name: str | None = None


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
    return MeOut(authenticated=True, email=user.email, role=role, display_name=display_name)


class SocialLinkIn(Schema):
    platform: str
    handle: str
    follower_count: int = 0


class CreatorOnboardingIn(Schema):
    invite_code: str
    display_name: str
    city: str = ""
    bio: str = ""
    niches: list[str] = []
    social_links: list[SocialLinkIn] = []


class BrandOnboardingIn(Schema):
    company_name: str
    cvr: str = ""
    website: str = ""
    city: str = ""


class OnboardingOut(Schema):
    role: str


def _require_no_profile(user):
    if user.role is not None:
        raise HttpError(409, "Account already has a profile")


@router.post("/onboarding/creator", response=OnboardingOut, auth=django_auth)
@transaction.atomic
def onboard_creator(request, payload: CreatorOnboardingIn):
    _require_no_profile(request.user)
    invite = (
        InviteCode.objects.select_for_update()
        .filter(code=payload.invite_code.strip(), is_active=True, used_by__isnull=True)
        .first()
    )
    if invite is None:
        raise HttpError(403, "Invalid or used invite code")
    profile = CreatorProfile.objects.create(
        user=request.user,
        display_name=payload.display_name.strip(),
        city=payload.city.strip(),
        bio=payload.bio.strip(),
    )
    for slug in payload.niches:
        tag = NicheTag.objects.filter(slug=slug).first()
        if tag:
            profile.niches.add(tag)
    for link in payload.social_links:
        if link.platform in SocialLink.Platform.values and link.handle.strip():
            SocialLink.objects.create(
                profile=profile,
                platform=link.platform,
                handle=link.handle.strip().lstrip("@"),
                follower_count=max(0, link.follower_count),
            )
    invite.used_by = request.user
    invite.used_at = timezone.now()
    invite.save(update_fields=["used_by", "used_at"])
    return OnboardingOut(role="creator")


@router.post("/onboarding/brand", response=OnboardingOut, auth=django_auth)
@transaction.atomic
def onboard_brand(request, payload: BrandOnboardingIn):
    _require_no_profile(request.user)
    BrandProfile.objects.create(
        user=request.user,
        company_name=payload.company_name.strip(),
        cvr=payload.cvr.strip(),
        website=payload.website.strip(),
        city=payload.city.strip(),
    )
    return OnboardingOut(role="brand")


class NicheOut(Schema):
    name: str
    slug: str


@router.get("/niches", response=list[NicheOut], auth=None)
def niches(request):
    return NicheTag.objects.all().order_by("name")
