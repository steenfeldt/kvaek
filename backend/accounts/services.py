"""Image pipeline: originals are never stored — resized WebP only."""

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
