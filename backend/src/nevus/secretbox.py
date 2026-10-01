# SPDX-License-Identifier: AGPL-3.0-only
"""Encrypting the few secrets neVus keeps in its database (the SMTP password, webhook tokens).

AES-256-GCM with a key derived from the server secret, so a copy of the database alone does not
reveal them; the secret file lives next to the database and is part of the backup.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIX = "v1:"


def _key(secret: bytes, purpose: str) -> bytes:
    return hashlib.sha256(b"nevus-secretbox|" + purpose.encode() + b"|" + secret).digest()


def seal(secret: bytes, plaintext: str, purpose: str = "settings") -> str:
    nonce = os.urandom(12)
    sealed = AESGCM(_key(secret, purpose)).encrypt(nonce, plaintext.encode(), purpose.encode())
    return PREFIX + base64.urlsafe_b64encode(nonce + sealed).decode()


def open_(secret: bytes, token: str, purpose: str = "settings") -> str:
    if not token.startswith(PREFIX):
        raise ValueError("unknown secret format")
    raw = base64.urlsafe_b64decode(token[len(PREFIX) :])
    return AESGCM(_key(secret, purpose)).decrypt(raw[:12], raw[12:], purpose.encode()).decode()
