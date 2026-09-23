"""Application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from nevus import __version__
from nevus.api.health import router as health_router
from nevus.config import Settings, get_settings
from nevus.db.engine import make_engine, make_session_factory
from nevus.logging import configure_logging, get_logger
from nevus.web.security import HostAllowlistMiddleware, SecurityHeadersMiddleware
from nevus.web.static import mount_frontend

log = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = make_engine(settings.effective_database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        log.info(
            "startup",
            version=__version__,
            database="sqlite" if settings.is_sqlite else "postgresql",
            role=settings.role,
        )
        yield
        engine.dispose()
        log.info("shutdown")

    app = FastAPI(
        title="neVus",
        version=__version__,
        description="Personal documentation and measurement aid for skin marks. Not a diagnostic tool.",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(HostAllowlistMiddleware, allowed_hosts=settings.allowed_hosts)

    app.include_router(health_router)
    mount_frontend(app, _static_dir(settings))
    return app


def _static_dir(settings: Settings) -> Path | None:
    if settings.static_dir:
        return settings.static_dir
    for candidate in (Path("/app/static"), Path(__file__).resolve().parents[3] / "frontend" / "dist"):
        if (candidate / "index.html").is_file():
            return candidate
    return None
