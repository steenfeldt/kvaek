"""Sync public channel metrics — run daily from cron with --jitter so the
calls do not stampede at the same second every night."""

import random
import time

from django.core.management.base import BaseCommand

from accounts.channel_sync import sync_channel, syncable
from accounts.models import SocialLink
from accounts.providers import ProviderError


class Command(BaseCommand):
    help = "Fetch public metrics for every syncable channel and append snapshots"

    def add_arguments(self, parser):
        parser.add_argument("--jitter", type=int, default=0, help="max random delay in seconds before starting")
        parser.add_argument("--platform", default="", help="only this platform")
        parser.add_argument("--pause", type=float, default=0.5, help="seconds between channels")

    def handle(self, *args, **options):
        if options["jitter"]:
            time.sleep(random.uniform(0, options["jitter"]))
        links = SocialLink.objects.select_related("profile").order_by("id")
        if options["platform"]:
            links = links.filter(platform=options["platform"])
        ok = failed = skipped = 0
        for link in links:
            if not syncable(link):
                skipped += 1
                continue
            try:
                sync_channel(link)
                ok += 1
            except ProviderError as e:
                failed += 1
                self.stderr.write(f"  ! {link.platform} @{link.handle}: {e}")
            time.sleep(options["pause"])
        self.stdout.write(f"channels: {ok} synced, {failed} failed, {skipped} skipped (no public lookup or not configured)")
