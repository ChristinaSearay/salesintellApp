"""Photos a rep adds to a customer's profile (shopfront, displays, stock).

The phone shrinks every photo before it is sent (frontend/src/lib/photo.js),
so these limits are guards against a bad client, not the normal size: a
1600px JPEG is ~200-500 KB, its thumbnail ~30 KB.
"""
import re
from enum import Enum


class PhotoSize(Enum):
    FULL = "full"
    THUMB = "thumb"


# Every photo is re-encoded as JPEG on the phone (which also strips EXIF, so a
# shop's GPS position never reaches the disk). Anything else is refused.
JPEG_MAGIC = b"\xff\xd8\xff"
JPEG_CONTENT_TYPE = "image/jpeg"
PHOTO_EXT = ".jpg"
META_EXT = ".json"

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_THUMB_BYTES = 300 * 1024
# The upload is JSON carrying both images as base64 (+33%), plus a caption.
MAX_UPLOAD_BYTES = (MAX_PHOTO_BYTES + MAX_THUMB_BYTES) * 4 // 3 + 64 * 1024

# Keeps one customer from eating the 1 GB deployed disk (~40 x 500 KB = 20 MB).
MAX_PHOTOS_PER_CUSTOMER = 40
MAX_CAPTION_CHARS = 200

# Photo ids are uuid4 hex; anything else in a URL is refused before it can
# become part of a file path.
PHOTO_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")

# A photo's bytes never change under its id, so the browser can keep it.
PHOTO_CACHE_CONTROL = "private, max-age=31536000, immutable"
