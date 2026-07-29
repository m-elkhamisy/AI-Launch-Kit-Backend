"""FastAPI transport shell with InnovationCity OAuth PKCE auth routes."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from launchkit.auth import auth_router
from launchkit.core.config import Settings, get_settings
from launchkit.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the transport application and register auth routes."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    app = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        version="0.1.0",
    )

    origins = [
        origin.strip()
        for origin in resolved_settings.auth_cors_origins.split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.dependency_overrides[get_settings] = lambda: resolved_settings
    return app


app = create_app()
