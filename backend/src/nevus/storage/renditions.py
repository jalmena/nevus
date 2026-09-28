"""Renditions: orientation-normalised, metadata-free JPEGs at fixed sizes, regenerable from the original."""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

SIZES: dict[str, int] = {"full": 2048, "preview": 1024, "thumb": 256}
QUALITY = 85


@dataclass(frozen=True)
class Rendition:
    kind: str
    data: bytes
    width: int
    height: int
    mime: str = "image/jpeg"


# EXIF orientation values and the transpose that puts the image upright
TRANSPOSE = {
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_270,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_90,
}


def make_renditions(
    original: bytes, orientation: int = 1, kinds: tuple[str, ...] = ("full", "preview", "thumb")
) -> list[Rendition]:
    """The original has had its metadata removed, so the orientation recorded at ingest is applied explicitly."""
    with Image.open(io.BytesIO(original)) as image:
        image.draft("RGB", (SIZES[kinds[0]], SIZES[kinds[0]]))  # cheaper JPEG decode when only a smaller size is needed
        upright = image.transpose(TRANSPOSE[orientation]) if orientation in TRANSPOSE else image
        rgb = upright.convert("RGB")
        out = []
        for kind in kinds:
            longest = SIZES[kind]
            copy = rgb.copy()
            copy.thumbnail((longest, longest), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            copy.save(buffer, format="JPEG", quality=QUALITY, optimize=True, progressive=True)
            out.append(Rendition(kind, buffer.getvalue(), copy.width, copy.height))
        return out
