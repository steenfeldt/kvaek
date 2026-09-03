"""Provider abstraction for social channels.

Phase A (now): public lookups where a platform offers them. Phase B (later,
after Meta/TikTok app review): OAuth. The Phase B methods exist on the base
class and raise NotImplementedError so the registry and UI logic stay uniform;
`supports_oauth` flips to True per provider when its flow is built.

Provider-specific field names never leave this package — every adapter
normalises into ChannelMetrics.
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class ProviderError(Exception):
    """Lookup failed for a reason the operator should see (logged verbatim)."""


class ProviderNotConfigured(ProviderError):
    """Missing API key/token; the provider is effectively off."""


class ChannelNotFound(ProviderError):
    """The handle does not resolve to an account."""


class AccountNotEligible(ProviderError):
    """The account exists but the platform will not expose it (e.g. a private
    or personal Instagram account). The message is meant for the creator."""


@dataclass(frozen=True)
class ResolvedChannel:
    external_id: str
    handle: str


@dataclass
class ChannelMetrics:
    followers: int | None
    posts: int | None
    engagement_rate: float | None
    handle: str
    raw: Any
    # Some platforms round public counts (YouTube: three significant figures).
    approximate: bool = False


@dataclass
class Credential:
    access_token: str
    refresh_token: str = ""
    expires_at: datetime | None = None
    scopes: list[str] = field(default_factory=list)


class ChannelProvider(ABC):
    platform: str = ""
    # Capability flags — the API exposes them so the UI can decide what to offer.
    supports_public_lookup: bool = False
    supports_oauth: bool = False
    approximate_counts: bool = False

    @property
    def configured(self) -> bool:
        """True when the keys the provider needs are present."""
        return True

    # --- Phase A ---
    def resolve_handle(self, handle: str) -> ResolvedChannel:
        raise ProviderNotConfigured(f"{self.platform} has no public lookup")

    def fetch_public_metrics(self, ref: ResolvedChannel) -> ChannelMetrics:
        raise ProviderNotConfigured(f"{self.platform} has no public lookup")

    # --- Phase B: defined now, built once app review clears ---
    def get_authorization_url(self, state: str) -> str:
        raise NotImplementedError(f"{self.platform} OAuth is not built yet")

    def exchange_code(self, code: str) -> Credential:
        raise NotImplementedError(f"{self.platform} OAuth is not built yet")

    def refresh_credential(self, cred: Credential) -> Credential:
        raise NotImplementedError(f"{self.platform} OAuth is not built yet")

    def fetch_authenticated_metrics(self, cred: Credential) -> ChannelMetrics:
        raise NotImplementedError(f"{self.platform} OAuth is not built yet")

    def revoke(self, cred: Credential) -> None:
        raise NotImplementedError(f"{self.platform} OAuth is not built yet")
