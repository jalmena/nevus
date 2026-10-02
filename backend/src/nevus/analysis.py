# SPDX-License-Identifier: AGPL-3.0-only
"""Analysis records: append-only results keyed by target, analyzer, version, parameters and input."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from nevus.db.models import Analysis


def params_hash(params: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def find(
    db: Session,
    target_type: str,
    target_id: uuid.UUID,
    analyzer: str,
    version: str,
    params: dict[str, Any],
    input_hash: str,
) -> Analysis | None:
    return db.scalar(
        select(Analysis).where(
            Analysis.target_type == target_type,
            Analysis.target_id == target_id,
            Analysis.analyzer == analyzer,
            Analysis.version == version,
            Analysis.params_hash == params_hash(params),
            Analysis.input_hash == input_hash,
        )
    )


def record(
    db: Session,
    *,
    target_type: str,
    target_id: uuid.UUID,
    analyzer: str,
    version: str,
    params: dict[str, Any],
    input_hash: str,
    outputs: dict[str, Any],
    status: str = "ok",
    error: str | None = None,
    decision: str = "automatic",
) -> Analysis:
    """Store a result once; the same analysis run again returns the existing row."""
    existing = find(db, target_type, target_id, analyzer, version, params, input_hash)
    if existing is not None:
        return existing
    row = Analysis(
        target_type=target_type,
        target_id=target_id,
        analyzer=analyzer,
        version=version,
        params=params,
        params_hash=params_hash(params),
        input_hash=input_hash,
        outputs=outputs,
        status=status,
        error=error,
        decision=decision,
    )
    db.add(row)
    db.flush()
    return row


def latest(db: Session, target_type: str, target_id: uuid.UUID, analyzer: str) -> Analysis | None:
    return db.scalar(
        select(Analysis)
        .where(Analysis.target_type == target_type, Analysis.target_id == target_id, Analysis.analyzer == analyzer)
        .order_by(Analysis.created_at.desc())
        .limit(1)
    )
