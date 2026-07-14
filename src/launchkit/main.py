"""FastAPI application composition for the V1 API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from launchkit.api import api_router
from launchkit.api.errors import register_error_handlers
from launchkit.api.middleware import RequestIdMiddleware
from launchkit.assets import AssetBlobStore, create_asset_store
from launchkit.core.config import Settings, get_settings
from launchkit.core.logging import configure_logging
from launchkit.persistence import Database, create_database


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
        allow_origins=[
            origin.strip()
            for origin in resolved_settings.frontend_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "Idempotency-Key", "Last-Event-ID"],
    )
    register_error_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
