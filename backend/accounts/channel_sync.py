"""Daily metric sync for channels whose platform offers a public lookup."""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import ChannelMetricSnapshot, SocialLink
from .providers import ProviderError, ResolvedChannel, get_provider

logger = logging.getLogger(__name__)


def syncable(link: SocialLink) -> bool:
    provider = get_provider(link.platform)
    return provider.supports_public_lookup and provider.configured


def sync_channel(link: SocialLink) -> ChannelMetricSnapshot:
    """Fetch public metrics and append a snapshot. On failure, bump
    `sync_failures` (three in a row downgrade the badge to stale) and re-raise."""
    provider = get_provider(link.platform)
    try:
        ref = (
            ResolvedChannel(external_id=link.external_id, handle=link.handle)
            if link.external_id
            else provider.resolve_handle(link.handle)
        )
        metrics = provider.fetch_public_metrics(ref)
        with transaction.atomic():
            if not link.external_id:
                # Binds the channel to the platform's stable id; unique per platform.
                link.external_id = ref.external_id
            if metrics.handle:
                link.handle = metrics.handle
            link.sync_failures = 0
            link.last_sync_at = timezone.now()
            link.save(update_fields=["external_id", "handle", "sync_failures", "last_sync_at"])
            return ChannelMetricSnapshot.objects.create(
                channel=link,
                followers=metrics.followers,
                posts=metrics.posts,
                engagement_rate=metrics.engagement_rate,
                raw=metrics.raw,
            )
    except IntegrityError as e:
        error: Exception = ProviderError(f"{link.platform} account is already linked to another profile ({e})")
    except ProviderError as e:
        error = e
    link.sync_failures += 1
    link.save(update_fields=["sync_failures"])
    logger.warning("channel sync failed: %s @%s (#%s): %s", link.platform, link.handle, link.sync_failures, error)
    raise error
