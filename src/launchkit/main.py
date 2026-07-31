"""FastAPI application composition: V1 API plus InnovationCity OAuth PKCE auth."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from launchkit.api import api_router
from launchkit.api.errors import register_error_handlers
from launchkit.api.middleware import RequestIdMiddleware
from launchkit.assets import AssetBlobStore, create_asset_store
from launchkit.auth import auth_router
from launchkit.core.config import Settings, get_settings
from launchkit.core.logging import configure_logging
from launchkit.persistence import Database, create_database


def _cors_origins(settings: Settings) -> list[str]:
    merged: list[str] = []
    for raw in (settings.frontend_origins, settings.auth_cors_origins):
        for origin in raw.split(","):
            origin = origin.strip()
            if origin and origin not in merged:
                merged.append(origin)
    return merged


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
    asset_store: AssetBlobStore | None = None,
) -> FastAPI:
    """Compose transport dependencies without requiring optional provider credentials."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        resolved_database = database or create_database(resolved_settings)
        resolved_asset_store = asset_store or create_asset_store(resolved_settings)
        application.state.settings = resolved_settings
        application.state.database = resolved_database
        application.state.asset_store = resolved_asset_store
        try:
            yield
        finally:
            await resolved_database.close()

    application = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        version="1.0.0",
        lifespan=lifespan,
    )
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(resolved_settings),
        # IC OAuth session cookies require credentialed CORS.
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "Last-Event-ID",
        ],
    )
    register_error_handlers(application)
    application.include_router(api_router)
    application.include_router(auth_router)
    application.dependency_overrides[get_settings] = lambda: resolved_settings
    return application


app = create_app()
