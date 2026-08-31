import pytest
from django.core.files.base import ContentFile

from accounts.gdpr import erase_user, export_user_data
from accounts.models import BrandProfile, CreatorProfile, ProfilePhoto, User, VerificationRequest
from billing.models import Payment
from campaigns.models import Campaign, Tier


@pytest.fixture
def creator_user(db):
    user = User.objects.create_user("creator-erase@example.com")
    profile = CreatorProfile.objects.create(user=user, display_name="Slet Mig", listed=True)
    ProfilePhoto.objects.create(profile=profile, image=ContentFile(b"fake", name="p.webp"))
    VerificationRequest.objects.create(creator=profile, evidence=ContentFile(b"fake", name="e.webp"))
    return user


def test_erase_creator_deletes_profile_and_files(creator_user):
    photo = ProfilePhoto.objects.get(profile__user=creator_user)
    evidence = VerificationRequest.objects.get(creator__user=creator_user)
    photo_storage, photo_name = photo.image.storage, photo.image.name
    ev_storage, ev_name = evidence.evidence.storage, evidence.evidence.name
    assert photo_storage.exists(photo_name) and ev_storage.exists(ev_name)

    erase_user(creator_user)
    creator_user.refresh_from_db()

    assert not CreatorProfile.objects.filter(user=creator_user).exists()
    assert not photo_storage.exists(photo_name)
    assert not ev_storage.exists(ev_name)
    assert creator_user.email.startswith("slettet-")
    assert not creator_user.is_active


def test_erase_brand_with_payments_anonymizes_but_keeps_financials(db):
    user = User.objects.create_user("brand-erase@example.com")
    brand = BrandProfile.objects.create(user=user, company_name="Hemmelig ApS", cvr="12345678")
    campaign = Campaign.objects.create(brand=brand, name="C", tier=Tier.STARTER)
    Payment.objects.create(campaign=campaign, amount_ore=29900, mollie_payment_id="tr_x")

    erase_user(user)
    brand.refresh_from_db()
    user.refresh_from_db()

    assert brand.company_name == "Anonymiseret virksomhed"
    assert brand.cvr == ""
    assert Payment.objects.filter(campaign__brand=brand).count() == 1
    assert user.email.startswith("slettet-")
    assert not user.is_active


def test_erase_brand_without_payments_deletes_profile(db):
    user = User.objects.create_user("brand-clean@example.com")
    BrandProfile.objects.create(user=user, company_name="Tom ApS")
    erase_user(user)
    assert not BrandProfile.objects.filter(user=user).exists()


def test_export_contains_core_data(creator_user):
    data = export_user_data(creator_user)
    assert data["user"]["email"] == "creator-erase@example.com"
    assert data["creator_profile"]["display_name"] == "Slet Mig"
    assert len(data["creator_profile"]["photos"]) == 1


def test_me_prompts_code_only_user_for_password(client, db):
    user = User.objects.create_user("code-only@example.com")
    client.force_login(user)
    assert client.get("/api/me").json()["prompt_password_setup"] is True


def test_me_does_not_prompt_with_password_or_google(client, db):
    from allauth.socialaccount.models import SocialAccount

    with_password = User.objects.create_user("has-pw@example.com", password="s3cret-s3cret")
    client.force_login(with_password)
    assert client.get("/api/me").json()["prompt_password_setup"] is False

    google = User.objects.create_user("google@example.com")
    SocialAccount.objects.create(user=google, provider="google", uid="g-123")
    client.force_login(google)
    assert client.get("/api/me").json()["prompt_password_setup"] is False


def test_password_prompt_dismiss_is_permanent(client, db):
    user = User.objects.create_user("keeps-codes@example.com")
    client.force_login(user)
    assert client.post("/api/me/password-prompt/dismiss").status_code == 200
    user.refresh_from_db()
    assert user.password_prompt_dismissed_at is not None
    assert client.get("/api/me").json()["prompt_password_setup"] is False
