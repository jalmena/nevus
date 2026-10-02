# SPDX-License-Identifier: AGPL-3.0-only
"""Blurring parts of a zone photo (FR-SES-05): intimate areas go before the photo is kept.

The regions are rectangles of the upright photo, as fractions of its width and height. Each is
pixelated into a handful of blocks and blurred over, past recognition, and the result is a new
photo that takes the old one's place in the session. The unblurred bytes are removed at once, not
kept in the trash: that is the point of the operation.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageFilter

from nevus.storage.renditions import TRANSPOSE

QUALITY = 92
BLOCKS = 8  # across the shorter side of a region: coarse enough that nothing in it can be made out


@dataclass(frozen=True)
class Region:
    x: float
    y: float
    width: float
    height: float


def blurred(original: bytes, orientation: int, regions: list[Region]) -> tuple[bytes, int, int]:
    """The upright photo with the regions made unrecognisable: JPEG bytes, width and height."""
    with Image.open(io.BytesIO(original)) as source:
        upright = source.transpose(TRANSPOSE[orientation]) if orientation in TRANSPOSE else source
        picture = upright.convert("RGB")
    width, height = picture.size
    for region in regions:
        left, top = max(0, round(region.x * width)), max(0, round(region.y * height))
        right = min(width, round((region.x + region.width) * width))
        bottom = min(height, round((region.y + region.height) * height))
        if right - left < 2 or bottom - top < 2:
            continue
        patch = picture.crop((left, top, right, bottom))
        block = max(8, min(patch.width, patch.height) // BLOCKS)
        coarse = patch.resize((max(1, patch.width // block), max(1, patch.height // block)), Image.Resampling.BOX)
        soft = coarse.resize(patch.size, Image.Resampling.NEAREST).filter(ImageFilter.GaussianBlur(radius=block))
        picture.paste(soft, (left, top))
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG", quality=QUALITY, optimize=True, progressive=True)
    return buffer.getvalue(), width, height
