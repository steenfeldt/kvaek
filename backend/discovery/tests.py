from accounts.models import BrandProfile, CreatorProfile, User


def test_deck_filters_on_hashtag(client, db):
    brand_user = User.objects.create_user("deckbrand@example.com")
    BrandProfile.objects.create(user=brand_user, company_name="Deck ApS", cvr="11111111")
    vegan = CreatorProfile.objects.create(
        user=User.objects.create_user("v@example.com"), display_name="Vegan", listed=True, bio_tags=["vegansk", "aarhus"]
    )
    CreatorProfile.objects.create(
        user=User.objects.create_user("r@example.com"), display_name="Runner", listed=True, bio_tags=["løb"]
    )
    CreatorProfile.objects.create(
        user=User.objects.create_user("h@example.com"), display_name="Hidden", listed=False, bio_tags=["vegansk"]
    )
    client.force_login(brand_user)

    assert len(client.get("/api/deck").json()) == 2
    for q in ("vegansk", "#Vegansk", " vegansk "):
        cards = client.get("/api/deck", {"tag": q}).json()
        assert [c["id"] for c in cards] == [vegan.id], q
    assert client.get("/api/deck", {"tag": "ukendt"}).json() == []
