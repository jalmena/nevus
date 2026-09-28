"""Remove every metadata segment from an uploaded photograph without touching its pixels.

Phones embed GPS coordinates, serial numbers, maker notes and thumbnails in every file. The privacy policy
keeps only the capture time and the orientation, both extracted here before the metadata is dropped. JPEG
and PNG are cleaned at the container level, so the compressed image data is byte-for-byte the original;
formats browsers cannot display (HEIC) are decoded and re-encoded as JPEG, which the record notes.
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass
from datetime import UTC, datetime

from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = False
Image.MAX_IMAGE_PIXELS = 60_000_000  # decompression-bomb guard; the API enforces its own lower limit

EXIF_DATETIME_ORIGINAL = 0x9003
EXIF_DATETIME = 0x0132
EXIF_ORIENTATION = 0x0112
EXIF_IFD = 0x8769

JPEG_KEEP = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,  # SOF
    0xC4,
    0xCC,
    0xDB,
    0xDD,
    0xE0,
}  # DHT, DAC, DQT, DRI, APP0 (JFIF)
JPEG_APP2 = 0xE2
JPEG_SOS = 0xDA
JPEG_EOI = 0xD9
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_DROP = {b"tEXt", b"zTXt", b"iTXt", b"eXIf", b"tIME"}


class UnsupportedImageError(ValueError):
    """The bytes are not an image we accept."""


@dataclass(frozen=True)
class Scrubbed:
    data: bytes
    mime: str
    width: int
    height: int
    orientation: int
    captured_at: datetime | None
    source_format: str
    re_encoded: bool


def scrub(data: bytes) -> Scrubbed:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            source_format = (image.format or "").upper()
            width, height = image.size
            exif = image.getexif()
            orientation = int(exif.get(EXIF_ORIENTATION, 1) or 1)
            captured_at = _capture_time(exif)
            if source_format == "JPEG":
                return Scrubbed(strip_jpeg(data), "image/jpeg", width, height, orientation, captured_at, "JPEG", False)
            if source_format == "PNG":
                return Scrubbed(strip_png(data), "image/png", width, height, orientation, captured_at, "PNG", False)
            # anything else (HEIC, WebP, TIFF...) is re-encoded as a high-quality JPEG without metadata
            converted = image.convert("RGB")
            buffer = io.BytesIO()
            converted.save(buffer, format="JPEG", quality=95, subsampling=0, optimize=True)
            return Scrubbed(
                buffer.getvalue(),
                "image/jpeg",
                width,
                height,
                orientation,
                captured_at,
                source_format or "UNKNOWN",
                True,
            )
    except (OSError, SyntaxError, ValueError) as error:
        raise UnsupportedImageError("The file is not a readable image.") from error


def _capture_time(exif: Image.Exif) -> datetime | None:
    raw = None
    try:
        raw = exif.get_ifd(EXIF_IFD).get(EXIF_DATETIME_ORIGINAL)
    except Exception:
        raw = None
    raw = raw or exif.get(EXIF_DATETIME)
    if not raw or not isinstance(raw, str):
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d %H:%M"):
        try:
            return datetime.strptime(raw.strip("\x00 "), fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def strip_jpeg(data: bytes) -> bytes:
    """Drop APPn (except JFIF and ICC), COM and other metadata segments; copy the scan data verbatim."""
    if data[:2] != b"\xff\xd8":
        raise UnsupportedImageError("Not a JPEG.")
    out = bytearray(b"\xff\xd8")
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            raise UnsupportedImageError("Corrupt JPEG marker structure.")
        marker = data[pos + 1]
        if marker == 0xFF:  # fill byte
            pos += 1
            continue
        if marker == JPEG_SOS:
            out += data[pos:]  # entropy-coded data, possibly more scans and the EOI marker
            return bytes(out)
        if marker == JPEG_EOI:
            out += data[pos : pos + 2]
            return bytes(out)
        length = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
        segment = data[pos : pos + 2 + length]
        keep = marker in JPEG_KEEP or (marker == JPEG_APP2 and segment[4:16] == b"ICC_PROFILE\x00")
        if keep:
            out += segment
        pos += 2 + length
    raise UnsupportedImageError("JPEG ended before its image data.")


def strip_png(data: bytes) -> bytes:
    """Drop textual, EXIF and time chunks; keep everything needed to decode and colour-manage the image."""
    if data[:8] != PNG_SIGNATURE:
        raise UnsupportedImageError("Not a PNG.")
    out = bytearray(PNG_SIGNATURE)
    pos = 8
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        kind = data[pos + 4 : pos + 8]
        end = pos + 12 + length
        if kind not in PNG_DROP:
            out += data[pos:end]
        pos = end
        if kind == b"IEND":
            break
    return bytes(out)
