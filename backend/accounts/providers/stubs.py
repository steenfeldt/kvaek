"""Platforms without a public lookup. They exist so the registry is complete
and the UI can read capability flags uniformly. Manual (screenshot)
verification is the only path for these until OAuth lands."""

from .base import ChannelProvider


class TikTokProvider(ChannelProvider):
    platform = "tiktok"  # OAuth only (Phase B); no public API.


class FacebookProvider(ChannelProvider):
    platform = "facebook"  # Pages only, needs a Page token (Phase B).


class SnapchatProvider(ChannelProvider):
    platform = "snapchat"  # Partner-gated; manual entry only.


class LinkedInProvider(ChannelProvider):
    platform = "linkedin"  # OIDC gives identity only, never follower counts.
