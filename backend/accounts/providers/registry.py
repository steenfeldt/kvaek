from .base import ChannelProvider
from .instagram import InstagramProvider
from .stubs import FacebookProvider, LinkedInProvider, SnapchatProvider, TikTokProvider
from .youtube import YouTubeProvider

PROVIDERS: dict[str, ChannelProvider] = {
    p.platform: p
    for p in (
        InstagramProvider(),
        TikTokProvider(),
        YouTubeProvider(),
        FacebookProvider(),
        SnapchatProvider(),
        LinkedInProvider(),
    )
}


def get_provider(platform: str) -> ChannelProvider:
    return PROVIDERS[platform]
