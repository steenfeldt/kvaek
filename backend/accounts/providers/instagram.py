"""Instagram via the Graph API `business_discovery` edge on our own connected
Instagram Business account. Only public Business/Creator accounts resolve.

Open question from the handoff: production use may need the "Instagram Public
Content Access" feature (app review). Works in development mode meanwhile.
"""

import requests
from django.conf import settings

from .base import AccountNotEligible, ChannelMetrics, ChannelProvider, ProviderError, ProviderNotConfigured, ResolvedChannel

GRAPH = "https://graph.facebook.com/v21.0"
NOT_ELIGIBLE = (
    "Instagram only shares numbers for public Business or Creator accounts. "
    "Switch your account to a Creator account (Settings → Account type) and try again."
)


class InstagramProvider(ChannelProvider):
    platform = "instagram"
    supports_public_lookup = True

    @property
    def configured(self) -> bool:
        return bool(settings.META_IG_USER_ID and settings.META_ACCESS_TOKEN)

    def _discover(self, handle: str) -> dict:
        if not self.configured:
            raise ProviderNotConfigured("META_IG_USER_ID / META_ACCESS_TOKEN are not set")
        handle = handle.lstrip("@")
        fields = f"business_discovery.username({handle}){{id,username,followers_count,media_count}}"
        res = requests.get(
            f"{GRAPH}/{settings.META_IG_USER_ID}",
            params={"fields": fields, "access_token": settings.META_ACCESS_TOKEN},
            timeout=15,
        )
        data = res.json() if res.content else {}
        if "error" in data or res.status_code != 200:
            err = data.get("error", {})
            # 110 = invalid parameter (non-business/private/unknown username), 24 = cannot find user.
            if err.get("code") in (110, 24):
                raise AccountNotEligible(NOT_ELIGIBLE)
            raise ProviderError(f"Instagram API {res.status_code}: {err.get('message') or res.text[:300]}")
        return data["business_discovery"]

    def resolve_handle(self, handle: str) -> ResolvedChannel:
        bd = self._discover(handle)
        return ResolvedChannel(external_id=str(bd["id"]), handle=bd["username"])

    def fetch_public_metrics(self, ref: ResolvedChannel) -> ChannelMetrics:
        # business_discovery is keyed by username; the stored id guards identity.
        bd = self._discover(ref.handle)
        if str(bd["id"]) != ref.external_id:
            raise ProviderError("Instagram username now belongs to a different account")
        return ChannelMetrics(
            followers=bd.get("followers_count"),
            posts=bd.get("media_count"),
            engagement_rate=None,
            handle=bd["username"],
            raw=bd,
        )
