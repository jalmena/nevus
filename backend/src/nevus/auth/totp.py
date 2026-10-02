# SPDX-License-Identifier: AGPL-3.0-only
"""A second factor for local accounts: time-based one-time codes (RFC 6238) and recovery codes.

The secret is shown once, as a QR code and in letters, when the person sets the factor up, and kept
sealed in the database (`secretbox`). A code is accepted within one step either side of the clock
and never twice. Recovery codes are random, shown once and stored hashed; each works once. Nothing
here depends on the network or on a third party.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

import segno

STEP_SECONDS = 30
DIGITS = 6
WINDOW = 1  # steps either side of now that are still accepted
RECOVERY_CODES = 10
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # nothing that reads like something else


def new_secret() -> str:
    """A 160-bit secret in base32, as authenticator apps expect it."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def current_counter(at: float | None = None) -> int:
    return int((time.time() if at is None else at) // STEP_SECONDS)


def code_for(secret: str, counter: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 10**DIGITS:0{DIGITS}d}"


def verify(secret: str, code: str, last_counter: int | None = None, at: float | None = None) -> int | None:
    """The counter the code matches, or None.

    A counter at or before the last one used is refused, so a code seen once cannot be replayed
    while its window is still open.
    """
    cleaned = code.replace(" ", "").strip()
    if len(cleaned) != DIGITS or not cleaned.isdigit():
        return None
    now = current_counter(at)
    for counter in range(now - WINDOW, now + WINDOW + 1):
        if last_counter is not None and counter <= last_counter:
            continue
        if hmac.compare_digest(code_for(secret, counter), cleaned):
            return counter
    return None


def provisioning_uri(secret: str, username: str, issuer: str = "neVus") -> str:
    label = quote(f"{issuer}:{username}", safe=":")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"
    )


def qr_svg(uri: str) -> str:
    """The provisioning URI as an SVG to scan from the screen, on its own white ground."""
    return str(segno.make(uri, error="m").svg_inline(scale=4, border=2, dark="#000000", light="#ffffff"))


def new_recovery_codes(count: int = RECOVERY_CODES) -> list[str]:
    """Codes like `h7kq2-m9xzt`: ten letters from a 31-letter alphabet, about 50 bits each."""

    def one() -> str:
        letters = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
        return f"{letters[:5]}-{letters[5:]}"

    return [one() for _ in range(count)]


def normalise_recovery_code(code: str) -> str:
    return code.strip().lower().replace(" ", "").replace("-", "")


def hash_recovery_code(code: str) -> str:
    """Recovery codes carry enough entropy for a plain hash; a key derivation would add nothing."""
    return hashlib.sha256(("nevus-recovery|" + normalise_recovery_code(code)).encode()).hexdigest()
