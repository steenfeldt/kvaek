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


def test_profile_patch_syncs_social_links(client, db):
    from django.utils import timezone

    from accounts.models import SocialLink

    user = User.objects.create_user("channels@example.com")
    profile = CreatorProfile.objects.create(user=user, display_name="Kanal")
    SocialLink.objects.create(
        profile=profile, platform="instagram", handle="old", follower_count=100, verified_at=timezone.now()
    )
    client.force_login(user)

    def patch(links):
        return client.patch(
            "/api/me/profile", {"social_links": links}, content_type="application/json"
        )

    # Add TikTok, bump Instagram followers without touching the handle.
    res = patch(
        [
            {"platform": "instagram", "handle": "@old", "follower_count": 150},
            {"platform": "tiktok", "handle": "@newtok", "follower_count": 20},
        ]
    )
    assert res.status_code == 200
    links = {s["platform"]: s for s in res.json()["social_links"]}
    assert links["instagram"] == {"platform": "instagram", "handle": "old", "follower_count": 150, "verified": True}
    assert links["tiktok"]["handle"] == "newtok"

    # Changing the handle drops verification; an empty handle removes the channel.
    res = patch([{"platform": "instagram", "handle": "fresh", "follower_count": 1}, {"platform": "tiktok", "handle": ""}])
    links = {s["platform"]: s for s in res.json()["social_links"]}
    assert list(links) == ["instagram"]
    assert links["instagram"]["verified"] is False

    # Any platform from the model's choices is accepted; unknown ones are ignored.
    res = patch(
        [
            {"platform": "instagram", "handle": "fresh", "follower_count": 1},
            {"platform": "youtube", "handle": "@tube", "follower_count": 5},
            {"platform": "myspace", "handle": "tom", "follower_count": 1},
        ]
    )
    assert sorted(s["platform"] for s in res.json()["social_links"]) == ["instagram", "youtube"]

    # Omitting the field leaves channels alone.
    res = client.patch("/api/me/profile", {"bio": "Hej"}, content_type="application/json")
    assert len(res.json()["social_links"]) == 2


def test_city_search_and_profile_city(client, db):
    from accounts.models import City

    aarhus = City.objects.create(dawa_id="a", name="Aarhus", municipality="Aarhus", municipality_code="0751")
    City.objects.create(dawa_id="b", name="Aars", municipality="Vesthimmerland", municipality_code="0820")
    City.objects.create(dawa_id="c", name="Sønderby", municipality="Assens", municipality_code="0420")
    City.objects.create(dawa_id="d", name="Sønderby", municipality="Kalundborg", municipality_code="0326")

    res = client.get("/api/cities", {"q": "aar"}).json()
    assert [c["label"] for c in res] == ["Aars", "Aarhus"]
    res = client.get("/api/cities", {"q": "Sønderby"}).json()
    assert [c["label"] for c in res] == ["Sønderby (Assens)", "Sønderby (Kalundborg)"]
    assert client.get("/api/cities").json() == []

    user = User.objects.create_user("city@example.com")
    CreatorProfile.objects.create(user=user, display_name="By")
    client.force_login(user)
    res = client.patch("/api/me/profile", {"city_id": aarhus.id}, content_type="application/json")
    assert res.json()["city"] == "Aarhus" and res.json()["city_id"] == aarhus.id
    # Absent key keeps the city, explicit null clears it.
    assert client.patch("/api/me/profile", {"bio": "x"}, content_type="application/json").json()["city"] == "Aarhus"
    assert client.patch("/api/me/profile", {"city_id": None}, content_type="application/json").json()["city"] == ""
    assert client.patch("/api/me/profile", {"city_id": 9999}, content_type="application/json").status_code == 422


def test_bio_hashtags_extracted_and_suggested(client, db):
    from accounts.services import extract_hashtags

    assert extract_hashtags("Mad fra #Aarhus og #vegansk. #aarhus igen, #zero-waste #x_1") == [
        "aarhus", "vegansk", "zero-waste", "x_1"
    ]
    assert extract_hashtags("ingen tags, email@example.com, #") == []
    with pytest.raises(ValueError):
        extract_hashtags(" ".join(f"#t{i}" for i in range(11)))

    user = User.objects.create_user("tags@example.com")
    CreatorProfile.objects.create(user=user, display_name="Tag", listed=True)
    client.force_login(user)
    res = client.patch("/api/me/profile", {"bio": "Hej #Aarhus #vegansk"}, content_type="application/json")
    assert res.status_code == 200 and res.json()["bio_tags"] == ["aarhus", "vegansk"]
    too_many = " ".join(f"#t{i}" for i in range(11))
    assert client.patch("/api/me/profile", {"bio": too_many}, content_type="application/json").status_code == 422

    other = User.objects.create_user("tags2@example.com")
    CreatorProfile.objects.create(user=other, display_name="Tag2", listed=True, bio_tags=["aarhus", "løb"])
    assert client.get("/api/hashtags", {"q": "a"}).json() == [{"tag": "aarhus", "count": 2}]
    assert [h["tag"] for h in client.get("/api/hashtags").json()] == ["aarhus", "løb", "vegansk"]


def _png() -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (40, 40), "red").save(buf, format="PNG")
    return buf.getvalue()


def test_single_profile_photo_and_portfolio(client, db):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from accounts.models import PortfolioItem

    user = User.objects.create_user("folio@example.com")
    profile = CreatorProfile.objects.create(user=user, display_name="Folio")
    client.force_login(user)

    # Uploading a second profile photo replaces the first.
    first = client.post("/api/me/photos", {"file": SimpleUploadedFile("a.png", _png(), "image/png")}).json()
    second = client.post("/api/me/photos", {"file": SimpleUploadedFile("b.png", _png(), "image/png")}).json()
    assert first["id"] != second["id"]
    assert profile.photos.count() == 1
    assert client.get("/api/me/profile").json()["photo"]["id"] == second["id"]

    # Portfolio: image and video items with text; title required.
    res = client.post(
        "/api/me/portfolio",
        {"file": SimpleUploadedFile("job.png", _png(), "image/png"), "title": "Kampagne for Kaffebar", "description": "3 reels"},
    )
    assert res.status_code == 200 and res.json()["media_type"] == "image"
    res = client.post(
        "/api/me/portfolio",
        {"file": SimpleUploadedFile("clip.mp4", b"\x00" * 100, "video/mp4"), "title": "Reel"},
    )
    assert res.status_code == 200 and res.json()["media_type"] == "video" and res.json()["url"].endswith(".mp4")
    assert client.post(
        "/api/me/portfolio", {"file": SimpleUploadedFile("x.png", _png(), "image/png"), "title": "  "}
    ).status_code == 422
    assert client.post(
        "/api/me/portfolio", {"file": SimpleUploadedFile("x.avi", b"\x00", "video/x-msvideo"), "title": "Nope"}
    ).status_code == 422

    items = client.get("/api/me/profile").json()["portfolio"]
    assert [i["title"] for i in items] == ["Kampagne for Kaffebar", "Reel"]
    item_id = items[0]["id"]
    res = client.patch(f"/api/me/portfolio/{item_id}", {"description": "5 reels"}, content_type="application/json")
    assert res.json()["description"] == "5 reels"
    assert client.delete(f"/api/me/portfolio/{item_id}").status_code == 200
    assert PortfolioItem.objects.filter(profile=profile).count() == 1
