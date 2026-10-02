# SPDX-License-Identifier: AGPL-3.0-only
"""Streaming encryption in the age format (age-encryption.org/v1) with a passphrase recipient.

Exports and backups are encrypted so that a copied file reveals nothing without the passphrase, and
in a standard format so they can be opened without neVus: `age -d nevus-export.age > export.zip`.
Data is processed in 64 KiB chunks, so a backup of several gigabytes never sits in memory.
"""

from __future__ import annotations

import base64
import hmac
import io
import os
from hashlib import sha256
from typing import BinaryIO

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

INTRO = b"age-encryption.org/v1\n"
CHUNK = 64 * 1024
TAG = 16
DEFAULT_WORK_FACTOR = 18  # age's default: about a second of scrypt on a desktop CPU


class AgeError(ValueError):
    """Wrong passphrase, damaged file, or not an age file."""


def _b64(data: bytes) -> bytes:
    return base64.b64encode(data).rstrip(b"=")


def _unb64(data: bytes) -> bytes:
    return base64.b64decode(data + b"=" * (-len(data) % 4), validate=True)


def _hkdf(key: bytes, salt: bytes, info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt or None, info=info).derive(key)


def _scrypt_key(passphrase: str, salt: bytes, log_n: int) -> bytes:
    return Scrypt(salt=b"age-encryption.org/v1/scrypt" + salt, length=32, n=2**log_n, r=8, p=1).derive(
        passphrase.encode()
    )


def _nonce(counter: int, last: bool) -> bytes:
    return counter.to_bytes(11, "big") + (b"\x01" if last else b"\x00")


class AgeWriter(io.RawIOBase):
    """A write-only file object that encrypts to `target`. Close it to write the final chunk."""

    def __init__(self, target: BinaryIO, passphrase: str, work_factor: int = DEFAULT_WORK_FACTOR) -> None:
        super().__init__()
        if not passphrase:
            raise AgeError("a passphrase is required")
        self._target = target
        file_key = os.urandom(16)
        salt = os.urandom(16)
        wrapped = ChaCha20Poly1305(_scrypt_key(passphrase, salt, work_factor)).encrypt(b"\x00" * 12, file_key, None)
        header = (
            INTRO + b"-> scrypt " + _b64(salt) + b" " + str(work_factor).encode() + b"\n" + _b64(wrapped) + b"\n---"
        )
        mac = hmac.new(_hkdf(file_key, b"", b"header"), header, sha256).digest()
        target.write(header + b" " + _b64(mac) + b"\n")
        nonce = os.urandom(16)
        target.write(nonce)
        self._aead = ChaCha20Poly1305(_hkdf(file_key, nonce, b"payload"))
        self._buffer = bytearray()
        self._counter = 0

    def writable(self) -> bool:
        return True

    def write(self, data: bytes | bytearray | memoryview) -> int:  # type: ignore[override]
        self._buffer += data
        # Hold back one full chunk: only close() knows which chunk is the last.
        while len(self._buffer) > CHUNK:
            self._emit(bytes(self._buffer[:CHUNK]), last=False)
            del self._buffer[:CHUNK]
        return len(data)

    def _emit(self, chunk: bytes, last: bool) -> None:
        self._target.write(self._aead.encrypt(_nonce(self._counter, last), chunk, None))
        self._counter += 1

    def close(self) -> None:
        if not self.closed:
            self._emit(bytes(self._buffer), last=True)
            self._buffer.clear()
            self._target.flush()
        super().close()


class AgeReader(io.RawIOBase):
    """A read-only file object that decrypts an age file encrypted to a passphrase."""

    def __init__(self, source: BinaryIO, passphrase: str, max_work_factor: int = 22) -> None:
        super().__init__()
        self._source = source
        file_key = self._unwrap(passphrase, max_work_factor)
        nonce = source.read(16)
        if len(nonce) != 16:
            raise AgeError("truncated file")
        self._aead = ChaCha20Poly1305(_hkdf(file_key, nonce, b"payload"))
        self._counter = 0
        self._pending = b""
        self._done = False
        self._next = source.read(CHUNK + TAG)

    def _unwrap(self, passphrase: str, max_work_factor: int) -> bytes:
        header = bytearray()
        line = self._source.readline()
        if line != INTRO:
            raise AgeError("not an age file")
        header += line
        stanza = self._source.readline()
        parts = stanza.split()
        if len(parts) != 4 or parts[0] != b"->" or parts[1] != b"scrypt":
            raise AgeError("not encrypted with a passphrase")
        header += stanza
        body = self._source.readline()
        header += body
        footer = self._source.readline()
        if not footer.startswith(b"--- "):
            raise AgeError("damaged header")
        salt, log_n = _unb64(parts[2]), int(parts[3])
        if not 1 <= log_n <= max_work_factor:
            raise AgeError("work factor out of range")
        try:
            file_key = ChaCha20Poly1305(_scrypt_key(passphrase, salt, log_n)).decrypt(
                b"\x00" * 12, _unb64(body.strip()), None
            )
        except Exception as error:
            raise AgeError("wrong passphrase") from error
        expected = hmac.new(_hkdf(file_key, b"", b"header"), bytes(header) + b"---", sha256).digest()
        if not hmac.compare_digest(expected, _unb64(footer[4:].strip())):
            raise AgeError("damaged header")
        return file_key

    def readable(self) -> bool:
        return True

    def _decrypt_next(self) -> None:
        chunk = self._next
        self._next = self._source.read(CHUNK + TAG)
        last = not self._next
        try:
            self._pending += self._aead.decrypt(_nonce(self._counter, last), chunk, None)
        except Exception as error:
            raise AgeError("damaged or truncated payload") from error
        self._counter += 1
        self._done = last

    def readinto(self, buffer: bytearray | memoryview) -> int:  # type: ignore[override]
        while not self._pending and not self._done:
            self._decrypt_next()
        count = min(len(buffer), len(self._pending))
        buffer[:count] = self._pending[:count]
        self._pending = self._pending[count:]
        return count


def encrypt_bytes(data: bytes, passphrase: str, work_factor: int = DEFAULT_WORK_FACTOR) -> bytes:
    out = io.BytesIO()
    with AgeWriter(out, passphrase, work_factor) as writer:
        writer.write(data)
    return out.getvalue()


def decrypt_bytes(data: bytes, passphrase: str) -> bytes:
    with AgeReader(io.BytesIO(data), passphrase) as reader:
        return reader.read()
