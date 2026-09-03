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
    assert links["instagram"]["handle"] == "old" and links["instagram"]["follower_count"] == 150
    assert links["instagram"]["verified"] is True and links["instagram"]["source"] == "self_reported"
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


def test_portfolio_reorder(client, db):
    from django.core.files.base import ContentFile

    from accounts.models import PortfolioItem

    user = User.objects.create_user("order@example.com")
    profile = CreatorProfile.objects.create(user=user, display_name="Order")
    a, b, c = [
        PortfolioItem.objects.create(
            profile=profile, media=ContentFile(b"x", name=f"{n}.webp"), media_type="image", title=n, sort_order=i
        )
        for i, n in enumerate("abc")
    ]
    client.force_login(user)
    res = client.put("/api/me/portfolio/order", {"ids": [c.id, a.id, b.id]}, content_type="application/json")
    assert res.status_code == 200
    assert [i["title"] for i in res.json()] == ["c", "a", "b"]
    assert [i["title"] for i in client.get("/api/me/profile").json()["portfolio"]] == ["c", "a", "b"]
    # Must name every item exactly once.
    assert client.put("/api/me/portfolio/order", {"ids": [a.id, b.id]}, content_type="application/json").status_code == 422
    assert client.put("/api/me/portfolio/order", {"ids": [a.id, b.id, c.id, 999]}, content_type="application/json").status_code == 422


def test_at_least_one_channel_required(client, db):
    from accounts.models import SocialLink

    user = User.objects.create_user("nochan@example.com")
    client.force_login(user)
    base = {"display_name": "Ingen", "accept_terms": True, "social_links": []}
    assert client.post("/api/onboarding/creator", base, content_type="application/json").status_code == 422
    assert not CreatorProfile.objects.filter(user=user).exists()
    base["social_links"] = [{"platform": "instagram", "handle": "ok", "follower_count": 1}]
    assert client.post("/api/onboarding/creator", base, content_type="application/json").status_code == 200

    res = client.patch("/api/me/profile", {"social_links": []}, content_type="application/json")
    assert res.status_code == 422
    res = client.patch(
        "/api/me/profile", {"social_links": [{"platform": "instagram", "handle": "  "}]}, content_type="application/json"
    )
    assert res.status_code == 422
    assert SocialLink.objects.filter(profile__user=user).count() == 1


def test_niche_suggestions_need_approval(client, db):
    from accounts.models import NicheTag

    NicheTag.objects.create(name="Mad", slug="mad")
    alice = User.objects.create_user("alice@example.com")
    bob = User.objects.create_user("bob@example.com")
    CreatorProfile.objects.create(user=alice, display_name="Alice", listed=True)
    CreatorProfile.objects.create(user=bob, display_name="Bob", listed=True)

    client.force_login(alice)
    res = client.post("/api/niches/suggest", {"name": "  padel   tennis "}, content_type="application/json")
    assert res.status_code == 200 and res.json() == {"name": "Padel tennis", "slug": "padel-tennis", "pending": True}
    # Visible to Alice, hidden from Bob and the public.
    assert [n["slug"] for n in client.get("/api/niches").json()] == ["mad", "padel-tennis"]
    client.force_login(bob)
    assert [n["slug"] for n in client.get("/api/niches").json()] == ["mad"]
    client.logout()
    assert [n["slug"] for n in client.get("/api/niches").json()] == ["mad"]

    # Alice can attach it; Bob cannot, and Bob is told it's already suggested.
    client.force_login(alice)
    res = client.patch("/api/me/profile", {"niches": ["padel-tennis", "mad"]}, content_type="application/json")
    assert sorted(n["slug"] for n in res.json()["niches"]) == ["mad", "padel-tennis"]
    client.force_login(bob)
    res = client.patch("/api/me/profile", {"niches": ["padel-tennis"]}, content_type="application/json")
    assert res.json()["niches"] == []
    assert client.post("/api/niches/suggest", {"name": "Padel tennis"}, content_type="application/json").status_code == 409

    # The deck only shows approved niches for Alice until staff approve.
    brand = User.objects.create_user("nb@example.com")
    BrandProfile.objects.create(user=brand, company_name="N ApS", cvr="22222222")
    client.force_login(brand)
    alice_card = next(c for c in client.get("/api/deck").json() if c["display_name"] == "Alice")
    assert alice_card["niches"] == ["Mad"]
    tag = NicheTag.objects.get(slug="padel-tennis")
    tag.status = NicheTag.Status.APPROVED
    tag.save()
    alice_card = next(c for c in client.get("/api/deck").json() if c["display_name"] == "Alice")
    assert sorted(alice_card["niches"]) == ["Mad", "Padel tennis"]

    # Pending cap and rejection.
    client.force_login(alice)
    for i in range(3):
        assert client.post("/api/niches/suggest", {"name": f"Niche {i}"}, content_type="application/json").status_code == 200
    assert client.post("/api/niches/suggest", {"name": "Niche 9"}, content_type="application/json").status_code == 409
    NicheTag.objects.filter(slug="niche-0").update(status=NicheTag.Status.REJECTED)
    assert client.post("/api/niches/suggest", {"name": "niche 0"}, content_type="application/json").status_code == 422


def test_channel_verification_and_states(client, db):
    from datetime import timedelta

    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.utils import timezone

    from accounts.models import ChannelMetricSnapshot, SocialLink, VerificationRequest

    user = User.objects.create_user("chanver@example.com")
    profile = CreatorProfile.objects.create(user=user, display_name="Chan", listed=True)
    link = SocialLink.objects.create(profile=profile, platform="tiktok", handle="chan", follower_count=5000)
    client.force_login(user)

    # Per-channel request → pending → staff approve → verified (manual).
    assert client.post("/api/me/channels/youtube/verification", {"file": SimpleUploadedFile("a.png", _png(), "image/png")}).status_code == 404
    res = client.post("/api/me/channels/tiktok/verification", {"file": SimpleUploadedFile("a.png", _png(), "image/png")})
    assert res.status_code == 200
    me = client.get("/api/me/profile").json()
    assert me["social_links"][0]["verification_status"] == "pending" and me["verified"] is False
    assert client.post("/api/me/channels/tiktok/verification", {"file": SimpleUploadedFile("b.png", _png(), "image/png")}).status_code == 409

    vr = VerificationRequest.objects.get(channel=link)
    from accounts.admin import VerificationRequestAdmin
    from django.contrib.admin.sites import AdminSite
    from django.test import RequestFactory

    req = RequestFactory().get("/admin/")
    req.user = User.objects.create_superuser("staff@example.com", password="x")
    VerificationRequestAdmin(VerificationRequest, AdminSite()).approve(req, VerificationRequest.objects.filter(pk=vr.pk))
    link.refresh_from_db()
    assert link.verification_method == "manual" and link.state == "verified"
    me = client.get("/api/me/profile").json()
    assert me["verified"] is True and me["social_links"][0]["state"] == "verified"
    assert me["social_links"][0]["verification_status"] is None

    # Brands see the number as self-reported until a snapshot exists, then live.
    brand = User.objects.create_user("vb@example.com")
    BrandProfile.objects.create(user=brand, company_name="V ApS", cvr="33333333")
    client.force_login(brand)
    card = next(c for c in client.get("/api/deck").json() if c["display_name"] == "Chan")
    assert card["verified"] is True
    assert card["socials"][0] == {"platform": "tiktok", "followers": 5000, "source": "self_reported", "approximate": False, "state": "verified", "verified": True, "synced_at": None}
    assert "handle" not in card["socials"][0]
    snap = ChannelMetricSnapshot.objects.create(channel=link, followers=5200, posts=40, raw={"x": 1})
    link.last_sync_at = timezone.now()
    link.save()
    card = next(c for c in client.get("/api/deck").json() if c["display_name"] == "Chan")
    assert card["socials"][0]["followers"] == 5200 and card["socials"][0]["source"] == "live"
    assert card["socials"][0]["synced_at"] is not None

    # Snapshots are append-only; stale after 3 failures or a quiet sync.
    snap.followers = 1
    with pytest.raises(ValueError):
        snap.save()
    link.sync_failures = 3
    assert link.state == "stale"
    link.sync_failures = 0
    link.last_sync_at = timezone.now() - timedelta(days=4)
    assert link.state == "stale"

    # Changing the handle drops the verification and the bound id.
    link.external_id = "123"
    link.last_sync_at = timezone.now()
    link.save()
    client.force_login(user)
    client.patch("/api/me/profile", {"social_links": [{"platform": "tiktok", "handle": "someone-else", "follower_count": 1}]}, content_type="application/json")
    link.refresh_from_db()
    assert link.verified_at is None and link.external_id is None and link.verification_method == "none"
    assert ChannelMetricSnapshot.objects.filter(channel=link).count() == 1  # history kept


def test_encrypted_credential_roundtrip(db):
    from accounts.models import ChannelCredential, SocialLink

    user = User.objects.create_user("cred@example.com")
    profile = CreatorProfile.objects.create(user=user, display_name="Cred")
    link = SocialLink.objects.create(profile=profile, platform="instagram", handle="c")
    ChannelCredential.objects.create(channel=link, access_token="secret-token", refresh_token="r", scopes_granted=["a"])
    stored = ChannelCredential.objects.get(channel=link)
    assert stored.access_token == "secret-token" and stored.refresh_token == "r"
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute("SELECT access_token FROM accounts_channelcredential WHERE channel_id = %s", [link.id])
        raw = cur.fetchone()[0]
    assert "secret-token" not in raw and raw.startswith("gAAAA")


def test_provider_registry_and_youtube_sync(db, monkeypatch, settings):
    from accounts.channel_sync import sync_channel, syncable
    from accounts.models import SocialLink
    from accounts.providers import PROVIDERS, ProviderError, get_provider
    from accounts.providers import youtube as yt

    assert set(PROVIDERS) == set(SocialLink.Platform.values)
    for platform in SocialLink.Platform.values:
        p = get_provider(platform)
        assert p.supports_oauth is False  # Phase B not built
        with pytest.raises(NotImplementedError):
            p.get_authorization_url("s")
    assert not get_provider("tiktok").supports_public_lookup

    user = User.objects.create_user("yt@example.com")
    profile = CreatorProfile.objects.create(user=user, display_name="YT")
    link = SocialLink.objects.create(profile=profile, platform="youtube", handle="@SomeChannel", follower_count=10)
    assert not syncable(link)  # no API key
    settings.YOUTUBE_API_KEY = "k"
    assert syncable(link)

    class FakeResponse:
        status_code = 200

        def __init__(self, items):
            self._items = items

        def json(self):
            return {"items": self._items}

    calls = []

    def fake_get(url, params, timeout):
        calls.append(params)
        item = {
            "id": "UC123",
            "snippet": {"customUrl": "@somechannel"},
            "statistics": {"subscriberCount": "12300", "videoCount": "87"},
        }
        return FakeResponse([item])

    monkeypatch.setattr(yt.requests, "get", fake_get)
    snap = sync_channel(link)
    link.refresh_from_db()
    assert link.external_id == "UC123" and link.handle == "somechannel" and link.sync_failures == 0
    assert snap.followers == 12300 and snap.posts == 87 and snap.raw["id"] == "UC123"
    assert calls[0]["forHandle"] == "@SomeChannel" and calls[1]["id"] == "UC123"

    # A failure bumps the counter and writes no snapshot.
    monkeypatch.setattr(yt.requests, "get", lambda url, params, timeout: FakeResponse([]))
    with pytest.raises(ProviderError):
        sync_channel(link)
    link.refresh_from_db()
    assert link.sync_failures == 1 and link.snapshots.count() == 1


def test_google_login_redirect(client, db, settings):
    settings.SOCIALACCOUNT_PROVIDERS = {
        "google": {"APPS": [{"client_id": "cid", "secret": "sec"}], "SCOPE": ["profile", "email"]}
    }
    res = client.post(
        "/_allauth/browser/v1/auth/provider/redirect",
        {"provider": "google", "callback_url": "http://testserver/auth/callback", "process": "login"},
    )
    assert res.status_code == 302
    assert res["Location"].startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "redirect_uri=http%3A%2F%2Ftestserver%2Faccounts%2Fgoogle%2Flogin%2Fcallback%2F" in res["Location"]
    assert "client_id=cid" in res["Location"]
