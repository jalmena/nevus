"""Content-addressed blob store on the data volume.

Files are named by the SHA-256 of their bytes under `blobs/originals/ab/cd/<sha256>` (immutable, scrubbed
originals) and `blobs/derived/ab/cd/<sha256>` (regenerable renditions). Writes are atomic renames from a
temporary file on the same filesystem, so a crash never leaves a half-written blob; directories are keyed
by hash, never by person, so the tree reveals nothing about who is who.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

MIN_FREE_BYTES = 2 * 1024**3


class InsufficientStorageError(OSError):
    """The data volume is nearly full; refusing to write."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class BlobStore:
    def __init__(self, root: Path, min_free_bytes: int = MIN_FREE_BYTES) -> None:
        self.root = root
        self.min_free_bytes = min_free_bytes
        (root / "originals").mkdir(parents=True, exist_ok=True)
        (root / "derived").mkdir(parents=True, exist_ok=True)
        (root / "tmp").mkdir(parents=True, exist_ok=True)

    def path(self, sha256: str, derived: bool = False) -> Path:
        kind = "derived" if derived else "originals"
        return self.root / kind / sha256[:2] / sha256[2:4] / sha256

    def exists(self, sha256: str, derived: bool = False) -> bool:
        return self.path(sha256, derived).is_file()

    def free_bytes(self) -> int:
        return shutil.disk_usage(self.root).free

    def put(self, data: bytes, derived: bool = False) -> str:
        """Store bytes, returning their hash; identical content is written once."""
        digest = sha256_hex(data)
        target = self.path(digest, derived)
        if target.is_file():
            return digest
        if self.free_bytes() - len(data) < self.min_free_bytes:
            raise InsufficientStorageError("Less than the reserved free space would remain on the data volume.")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=self.root / "tmp")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp_name, 0o640)
            os.replace(tmp_name, target)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise
        return digest

    def delete(self, sha256: str, derived: bool = False) -> None:
        self.path(sha256, derived).unlink(missing_ok=True)

    def verify(self, sha256: str, derived: bool = False) -> bool:
        path = self.path(sha256, derived)
        return path.is_file() and sha256_hex(path.read_bytes()) == sha256
