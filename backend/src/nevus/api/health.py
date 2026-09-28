"""Health endpoint for orchestration and the CasaOS check."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

from nevus import __version__
from nevus.config import Settings
from nevus.db.engine import check_database

router = APIRouter()


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    database: Literal["ok", "unavailable"]
    storage: Literal["ok", "unavailable"]


@router.get("/healthz", response_model=Health, tags=["system"])
def healthz(request: Request) -> Health:
    settings: Settings = request.app.state.settings
    database_ok = check_database(request.app.state.engine)
    storage_ok = settings.data_dir.is_dir() and _writable(settings)
    return Health(
        status="ok" if database_ok and storage_ok else "degraded",
        version=__version__,
        database="ok" if database_ok else "unavailable",
        storage="ok" if storage_ok else "unavailable",
    )


def _writable(settings: Settings) -> bool:
    return os.access(settings.data_dir, os.W_OK)
