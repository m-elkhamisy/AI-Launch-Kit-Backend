"""FastAPI transport shell; business routes are intentionally deferred."""

from fastapi import FastAPI

from launchkit.core.config import Settings, get_settings
from launchkit.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the transport application without registering business routes."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    return FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        version="0.1.0",
    )


app = create_app()
