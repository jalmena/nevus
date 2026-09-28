# SPDX-License-Identifier: AGPL-3.0-only
"""Body map data for API clients and reports; the frontend bundles the same file."""

from __future__ import annotations

from fastapi import APIRouter

from nevus.bodymap import BodyMap, body_map

router = APIRouter(prefix="/api/bodymap", tags=["bodymap"])


@router.get("", response_model=BodyMap)
def get_body_map() -> BodyMap:
    return body_map()
