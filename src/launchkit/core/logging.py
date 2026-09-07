"""Structured logging configuration."""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from launchkit.core.config import Settings


def _renderer(log_json: bool) -> structlog.types.Processor:
    if log_json:
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())


def configure_logging(settings: Settings) -> None:
    """Configure stdlib and structlog output for the current process."""

    logging.basicConfig(
        format="%(message)s",
        level=settings.log_level,
        stream=sys.stdout,
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_service_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Without this, logger.exception() only sets "exc_info": true and drops
            # the traceback — which is why UAT job_failed lines were unactionable.
            structlog.processors.format_exc_info,
            _renderer(settings.log_json),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping()[settings.log_level]
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def add_service_context(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Add stable service metadata to a structured log event."""

    event_dict["service"] = "launchkit"
    return event_dict
