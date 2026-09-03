"""YouTube Data API v3 — public channel statistics with a plain API key."""

import requests
from django.conf import settings

from .base import ChannelMetrics, ChannelNotFound, ChannelProvider, ProviderError, ProviderNotConfigured, ResolvedChannel

API = "https://www.googleapis.com/youtube/v3/channels"


class YouTubeProvider(ChannelProvider):
    platform = "youtube"
    supports_public_lookup = True
    # Public subscriber counts are rounded to three significant figures.
    approximate_counts = True

    @property
    def configured(self) -> bool:
        return bool(settings.YOUTUBE_API_KEY)

    def _channel(self, **params) -> dict:
        if not self.configured:
            raise ProviderNotConfigured("YOUTUBE_API_KEY is not set")
        res = requests.get(
            API,
            params={**params, "part": "snippet,statistics", "key": settings.YOUTUBE_API_KEY},
            timeout=15,
        )
        if res.status_code != 200:
            raise ProviderError(f"YouTube API {res.status_code}: {res.text[:300]}")
        items = res.json().get("items") or []
        if not items:
            raise ChannelNotFound("No YouTube channel matches that handle")
        return items[0]

    @staticmethod
    def _handle(item: dict, fallback: str) -> str:
        return (item.get("snippet", {}).get("customUrl") or fallback).lstrip("@")

    def resolve_handle(self, handle: str) -> ResolvedChannel:
        item = self._channel(forHandle="@" + handle.lstrip("@"))
        return ResolvedChannel(external_id=item["id"], handle=self._handle(item, handle))

    def fetch_public_metrics(self, ref: ResolvedChannel) -> ChannelMetrics:
        item = self._channel(id=ref.external_id)
        stats = item.get("statistics", {})
        hidden = stats.get("hiddenSubscriberCount")
        return ChannelMetrics(
            followers=None if hidden or "subscriberCount" not in stats else int(stats["subscriberCount"]),
            posts=int(stats["videoCount"]) if stats.get("videoCount") is not None else None,
            engagement_rate=None,
            handle=self._handle(item, ref.handle),
            raw=item,
            approximate=True,
        )
