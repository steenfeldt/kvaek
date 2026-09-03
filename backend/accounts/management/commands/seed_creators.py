"""Populate the database with fake but real-looking Danish creators.

Seeded accounts use the email domain @seed.invalid so they are easy to
identify and remove: `manage.py seed_creators --clear`.
"""

import random
from io import BytesIO

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from PIL import Image

from accounts.models import City, CreatorProfile, NicheTag, SocialLink, User
from accounts.services import process_profile_image

SEED_DOMAIN = "seed.invalid"

FIRST_NAMES = [
    "Emma", "Sofie", "Freja", "Ida", "Clara", "Laura", "Anna", "Alma", "Josefine", "Mathilde",
    "Karla", "Astrid", "Maja", "Signe", "Nanna", "Cecilie", "Katrine", "Louise", "Amalie", "Thea",
    "Oliver", "Noah", "Emil", "Victor", "Magnus", "Frederik", "Mikkel", "Rasmus", "Sebastian", "Malthe",
    "Oscar", "Elias", "Christian", "Mads", "Jonas", "Tobias", "Nikolaj", "Andreas", "Simon", "Kasper",
]
LAST_NAMES = [
    "Nielsen", "Jensen", "Hansen", "Pedersen", "Andersen", "Christensen", "Larsen", "Sørensen",
    "Rasmussen", "Jørgensen", "Petersen", "Madsen", "Kristensen", "Olsen", "Thomsen", "Christiansen",
    "Poulsen", "Johansen", "Møller", "Mortensen", "Knudsen", "Jakobsen", "Holm", "Schmidt", "Lund",
]
CITIES = [
    "København", "Aarhus", "Odense", "Aalborg", "Esbjerg", "Randers", "Kolding", "Horsens",
    "Vejle", "Roskilde", "Herning", "Silkeborg", "Næstved", "Fredericia", "Helsingør",
]
NICHES = [
    "Mad", "Mode", "Fitness", "Gaming", "Beauty", "Rejser", "Bolig", "Familie",
    "Musik", "Outdoor", "Foto", "Bæredygtighed",
]
BIO_TEMPLATES = {
    "Mad": ["Madglad {city}-bo. Opskrifter, restaurantbesøg og alt med smør.", "Hjemmebag og hverdagsmad fra mit køkken i {city}."],
    "Mode": ["Outfits, secondhand-fund og styling fra {city}.", "Mode på budget — viser hvordan i {city}s gader."],
    "Fitness": ["PT og løbeglad. Træningsprogrammer og ærlige før/efter.", "Styrketræning og meal prep — uden filter."],
    "Gaming": ["Streamer hygge-gaming og indie-perler.", "Gaming-klip og setups. Altid co-op."],
    "Beauty": ["Makeup-tutorials og hudpleje til hverdagen.", "Cruelty-free beauty og ærlige anmeldelser."],
    "Rejser": ["Weekendture og skjulte perler i Europa.", "Rejser på budget — {city} som base."],
    "Bolig": ["Indretning af min lejlighed i {city}, ét DIY-projekt ad gangen.", "Loppefund og nordisk indretning."],
    "Familie": ["Familieliv med to små i {city}. Hverdagskaos og hyggelige stunder.", "Mor-liv, LEGO på gulvet og nem aftensmad."],
    "Musik": ["Sangskriver og livestreams fra øvelokalet.", "Vinylsamler og koncertanmeldelser."],
    "Outdoor": ["Vandreture, vinterbadning og friluftsliv.", "Ud i naturen — telt, bål og kaffe."],
    "Foto": ["Gadefotografi fra {city} og analoge eksperimenter.", "Fotograf med kærlighed til gyldne timer."],
    "Bæredygtighed": ["Grønnere hverdag uden pegefingre. Tips der virker.", "Zero waste-forsøg og genbrugsfund i {city}."],
}
HANDLE_SUFFIXES = ["", "", ".dk", "_", "dk", "official"]

PALETTE = [(201, 111, 74), (147, 67, 42), (43, 33, 24), (107, 93, 79), (220, 181, 154), (95, 46, 34)]


def _fallback_image(name: str, size: int = 800) -> BytesIO:
    """Offline stand-in: two-tone gradient with initials."""
    c1, c2 = random.sample(PALETTE, 2)
    img = Image.new("RGB", (size, size))
    for y in range(size):
        t = y / size
        row = tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))
        img.paste(row, (0, y, size, y + 1))
    buf = BytesIO()
    img.save(buf, "JPEG", quality=85)
    buf.seek(0)
    return buf


def _photo(seed: int, name: str) -> BytesIO:
    try:
        res = requests.get(f"https://i.pravatar.cc/800?img={seed % 70 + 1}", timeout=5)
        res.raise_for_status()
        return BytesIO(res.content)
    except Exception:
        return _fallback_image(name)


def _handle(name: str) -> str:
    base = slugify(name).replace("-", "")
    suffix = random.choice(HANDLE_SUFFIXES)
    if random.random() < 0.3:
        suffix += str(random.randint(1, 99))
    return (base + suffix)[:30]


def _followers() -> int:
    # Nano-heavy distribution within the 1k-50k segment.
    if random.random() < 0.7:
        return random.randint(1_000, 10_000)
    return random.randint(10_000, 50_000)


class Command(BaseCommand):
    help = "Seed the database with fake but real-looking Danish creators"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=25)
        parser.add_argument("--clear", action="store_true", help="Delete previously seeded creators and exit")

    def handle(self, *args, **options):
        if options["clear"]:
            users = User.objects.filter(email__endswith=f"@{SEED_DOMAIN}")
            count = users.count()
            for user in users:
                profile = getattr(user, "creator_profile", None)
                if profile:
                    for photo in profile.photos.all():
                        photo.image.delete(save=False)
                user.delete()
            self.stdout.write(f"Removed {count} seeded creators.")
            return

        tags = {name: NicheTag.objects.get_or_create(name=name, defaults={"slug": slugify(name)})[0] for name in NICHES}

        created = 0
        attempts = 0
        while created < options["count"] and attempts < options["count"] * 5:
            attempts += 1
            first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
            name = f"{first} {last}"
            email = f"{slugify(name)}{random.randint(1, 999)}@{SEED_DOMAIN}"
            if User.objects.filter(email=email).exists():
                continue

            city = random.choice(CITIES)
            main_niche = random.choice(NICHES)
            bio = random.choice(BIO_TEMPLATES[main_niche]).format(city=city)
            # Needs `sync_cities` to have run; otherwise the profile has no city.
            city_obj = City.objects.filter(name=city).order_by("id").first()

            user = User.objects.create_user(email)
            profile = CreatorProfile.objects.create(
                user=user,
                display_name=name,
                city=city_obj,
                bio=bio,
                listed=True,
                verified=random.random() < 0.25,
            )
            niches = {main_niche} | set(random.sample(NICHES, random.randint(0, 2)))
            profile.niches.set([tags[n] for n in niches])

            handle = _handle(name)
            SocialLink.objects.create(
                profile=profile, platform=SocialLink.Platform.INSTAGRAM, handle=handle, follower_count=_followers()
            )
            if random.random() < 0.6:
                SocialLink.objects.create(
                    profile=profile, platform=SocialLink.Platform.TIKTOK, handle=handle, follower_count=_followers()
                )

            for i in range(random.randint(1, 3)):
                raw = _photo(created * 3 + i, name)
                profile.photos.create(image=process_profile_image(raw), sort_order=i)

            created += 1
            self.stdout.write(f"  + {name} ({city}, {', '.join(sorted(niches))})")

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} creators."))
