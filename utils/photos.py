"""Photos a rep adds to a customer's profile.

The point is judgement on the next visit — what the shopfront looks like, how
our stock is displayed, whose cabinets sit next to ours — so photos belong to
the customer, not to one note.

Storage is the deployed persistent disk, under the notes directory
(photos/<code>/), so it needs no extra configuration. Each photo is three
files sharing one id: <id>.jpg, <id>.thumb.jpg and <id>.json (caption + time).
The .json is written last and removed first, so a half-written upload never
shows up in a listing, and there is no shared index file for two uploads to
race on. Photos never go into the notes JSON: the attention queue reads every
notes file on every load, and images there would slow the busiest screen.

Nothing here touches the recommender — photos are for reps to look at.
"""
import base64
import binascii
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import List

from constants.config import PHOTOS_DIR
from constants.photos import (
    JPEG_MAGIC,
    MAX_CAPTION_CHARS,
    MAX_PHOTO_BYTES,
    MAX_PHOTOS_PER_CUSTOMER,
    MAX_THUMB_BYTES,
    META_EXT,
    PHOTO_EXT,
    PHOTO_ID_PATTERN,
    PhotoSize,
)


@dataclass(frozen=True)
class Photo:
    id: str
    ts: str
    caption: str = ""


def _dir(code: str) -> str:
    return os.path.join(PHOTOS_DIR, code)


def _file(code: str, photo_id: str, size: PhotoSize) -> str:
    suffix = PHOTO_EXT if size is PhotoSize.FULL else f".{PhotoSize.THUMB.value}{PHOTO_EXT}"
    return os.path.join(_dir(code), photo_id + suffix)


def _meta(code: str, photo_id: str) -> str:
    return os.path.join(_dir(code), photo_id + META_EXT)


def _valid_id(photo_id: str) -> str:
    if not PHOTO_ID_PATTERN.match(photo_id or ""):
        raise ValueError("Unknown photo.")
    return photo_id


def _decode_jpeg(b64: str, limit: int, what: str) -> bytes:
    try:
        data = base64.b64decode(b64 or "", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"The {what} didn't upload properly — try again.") from exc
    if not data.startswith(JPEG_MAGIC):
        raise ValueError(f"The {what} isn't a JPEG.")
    if len(data) > limit:
        raise ValueError(f"The {what} is too large ({len(data) // 1024} KB).")
    return data


def list_photos(code: str) -> List[Photo]:
    """Newest first."""
    try:
        names = os.listdir(_dir(code))
    except FileNotFoundError:
        return []
    out: List[Photo] = []
    for name in names:
        photo_id, ext = os.path.splitext(name)
        if ext != META_EXT:
            continue
        with open(os.path.join(_dir(code), name), encoding="utf-8") as fh:
            d = json.load(fh)
        out.append(Photo(**{k: d[k] for k in Photo.__dataclass_fields__ if k in d}))
    return sorted(out, key=lambda p: p.ts, reverse=True)


def add_photo(code: str, image_b64: str, thumb_b64: str, caption: str = "") -> Photo:
    caption = (caption or "").strip()
    if len(caption) > MAX_CAPTION_CHARS:
        raise ValueError(f"Keep the caption under {MAX_CAPTION_CHARS} characters.")
    if len(list_photos(code)) >= MAX_PHOTOS_PER_CUSTOMER:
        raise ValueError(f"This customer already has {MAX_PHOTOS_PER_CUSTOMER} photos — "
                         "delete an old one first.")
    image = _decode_jpeg(image_b64, MAX_PHOTO_BYTES, "photo")
    thumb = _decode_jpeg(thumb_b64, MAX_THUMB_BYTES, "thumbnail")

    photo = Photo(id=uuid.uuid4().hex,
                  ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  caption=caption)
    os.makedirs(_dir(code), exist_ok=True)
    with open(_file(code, photo.id, PhotoSize.FULL), "wb") as fh:
        fh.write(image)
    with open(_file(code, photo.id, PhotoSize.THUMB), "wb") as fh:
        fh.write(thumb)
    with open(_meta(code, photo.id), "w", encoding="utf-8") as fh:   # last: makes it visible
        json.dump(asdict(photo), fh, indent=2)
    return photo


def read_photo(code: str, photo_id: str, size: PhotoSize) -> bytes:
    """The image bytes; FileNotFoundError if there is no such photo."""
    _valid_id(photo_id)
    if not os.path.exists(_meta(code, photo_id)):
        raise FileNotFoundError(photo_id)
    with open(_file(code, photo_id, size), "rb") as fh:
        return fh.read()


def delete_photo(code: str, photo_id: str) -> bool:
    _valid_id(photo_id)
    try:
        os.remove(_meta(code, photo_id))   # first: hides it straight away
    except FileNotFoundError:
        return False
    for size in PhotoSize:
        try:
            os.remove(_file(code, photo_id, size))
        except FileNotFoundError:
            pass
    return True


def photos_payload(code: str) -> List[dict]:
    return [asdict(p) for p in list_photos(code)]
