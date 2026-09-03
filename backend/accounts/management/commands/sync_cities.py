"""Sync the City table with DAWA (Dataforsyningen) place names of type "by".

Open public data, no API key. Run at deploy and occasionally afterwards; the
list changes rarely. Rows that disappear upstream are deleted (profiles keep a
NULL city via SET_NULL).
"""

import requests
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import City

DAWA_URL = "https://api.dataforsyningen.dk/stednavne2"


class Command(BaseCommand):
    help = "Sync Danish towns from DAWA into the City table"

    @transaction.atomic
    def handle(self, *args, **options):
        res = requests.get(
            DAWA_URL, params={"hovedtype": "Bebyggelse", "undertype": "by"}, timeout=120
        )
        res.raise_for_status()
        seen, created, updated = set(), 0, 0
        for entry in res.json():
            # Secondary names are alternative spellings of a place already listed.
            if entry.get("brugsprioritet") != "primær":
                continue
            sted = entry["sted"]
            kommune = (sted.get("kommuner") or [{}])[0]
            _, was_created = City.objects.update_or_create(
                dawa_id=sted["id"],
                defaults={
                    "name": entry["navn"],
                    "municipality": kommune.get("navn", ""),
                    "municipality_code": kommune.get("kode", ""),
                },
            )
            seen.add(sted["id"])
            created += was_created
            updated += not was_created
        deleted, _ = City.objects.exclude(dawa_id__in=seen).delete()
        self.stdout.write(f"cities: {created} created, {updated} updated, {deleted} deleted")
