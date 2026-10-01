# SPDX-License-Identifier: AGPL-3.0-only
"""Job kinds. Each kind registers itself at import time of the module that defines it."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from nevus.config import Settings
from nevus.storage.blobs import BlobStore


@dataclass
class JobContext:
    db: Session
    store: BlobStore
    settings: Settings


Loader = Callable[[JobContext, dict[str, Any]], Any]
Computer = Callable[[Any], Any]
Storer = Callable[[JobContext, dict[str, Any], Any], None]
Failer = Callable[[JobContext, dict[str, Any], str], None]


@dataclass(frozen=True)
class JobKind:
    name: str
    load: Loader
    """Main process. Returns the picklable input for `compute`, or None when there is nothing to do."""
    compute: Computer
    """Worker process. Must be a module-level function: it is pickled by name."""
    store: Storer
    """Main process. Writes the result."""
    timeout: float = 120.0
    max_attempts: int = 3
    on_failure: Failer | None = None
    """Main process. Called once when the last attempt has failed, to tell whoever is waiting."""


KINDS: dict[str, JobKind] = {}


def register(kind: JobKind) -> JobKind:
    KINDS[kind.name] = kind
    return kind


def identity(value: Any) -> Any:
    """`compute` for kinds that do all their work in `load` and `store`."""
    return value
