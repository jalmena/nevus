# SPDX-License-Identifier: AGPL-3.0-only
"""The age format, checked against the reference implementation in both directions."""

from __future__ import annotations

import os

import pyrage
import pytest

from nevus.agecrypt import CHUNK, AgeError, decrypt_bytes, encrypt_bytes

SIZES = [0, 1, CHUNK - 1, CHUNK, CHUNK + 1, 3 * CHUNK, 3 * CHUNK + 17]


@pytest.mark.parametrize("size", SIZES)
def test_what_we_encrypt_the_reference_decrypts(size: int) -> None:
    data = os.urandom(size)
    sealed = encrypt_bytes(data, "correct horse battery", work_factor=10)
    assert pyrage.passphrase.decrypt(sealed, "correct horse battery") == data


# The reference always uses its full scrypt work factor (seconds per call), so it encrypts only the
# cases that differ for the reader: nothing, a payload ending exactly on a chunk, and a partial tail.
@pytest.mark.parametrize("size", [0, CHUNK, 3 * CHUNK + 17])
def test_what_the_reference_encrypts_we_decrypt(size: int) -> None:
    data = os.urandom(size)
    assert decrypt_bytes(pyrage.passphrase.encrypt(data, "correct horse battery"), "correct horse battery") == data


@pytest.mark.parametrize("size", SIZES)
def test_every_chunk_boundary_survives_a_round_trip(size: int) -> None:
    data = os.urandom(size)
    assert decrypt_bytes(encrypt_bytes(data, "correct horse battery", work_factor=10), "correct horse battery") == data


def test_a_wrong_passphrase_or_a_damaged_file_is_refused() -> None:
    sealed = encrypt_bytes(b"secret notes" * 1000, "right one", work_factor=10)
    with pytest.raises(AgeError):
        decrypt_bytes(sealed, "wrong one")
    damaged = bytearray(sealed)
    damaged[-5] ^= 0x01
    with pytest.raises(AgeError):
        decrypt_bytes(bytes(damaged), "right one")
    with pytest.raises(AgeError):
        decrypt_bytes(sealed[: len(sealed) // 2], "right one")
    with pytest.raises(AgeError):
        decrypt_bytes(b"not age at all\n", "right one")
