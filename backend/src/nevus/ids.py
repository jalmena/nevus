"""UUIDv7 identifiers (RFC 9562): time-ordered, so indexes stay local and clients can mint them offline."""

from __future__ import annotations

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    milliseconds = time.time_ns() // 1_000_000
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFF_FFFF_FFFF_FFFF
    value = (milliseconds << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return uuid.UUID(int=value)
