"""Image pipeline: originals are never stored — resized WebP only."""

import re
import uuid
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_DIMENSION = 800
WEBP_QUALITY = 82


def process_profile_image(uploaded_file, max_dimension: int = MAX_DIMENSION) -> ContentFile:
    img = Image.open(uploaded_file)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((max_dimension, max_dimension))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, "WEBP", quality=WEBP_QUALITY)
    return ContentFile(buf.getvalue(), name=f"{uuid.uuid4().hex}.webp")


MAX_BIO_TAGS = 10
MAX_TAG_LENGTH = 30
# '#' followed by a word: letters/digits/underscore, optional inner hyphens. \w is
# unicode-aware, so æøå count as letters.
HASHTAG_RE = re.compile(r"#(\w(?:[\w-]*\w)?)")


def extract_hashtags(text: str) -> list[str]:
    """Hashtags in `text`, lowercased, deduplicated, in order of appearance.
    Raises ValueError when there are too many or one is too long."""
    tags: list[str] = []
    for match in HASHTAG_RE.finditer(text):
        tag = match.group(1).lower()
        if len(tag) > MAX_TAG_LENGTH:
            raise ValueError(f"Hashtag too long: #{tag[:MAX_TAG_LENGTH]}…")
        if tag not in tags:
            tags.append(tag)
    if len(tags) > MAX_BIO_TAGS:
        raise ValueError(f"At most {MAX_BIO_TAGS} hashtags")
    return tags
