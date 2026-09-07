import json

import pytest
import structlog

from launchkit.core.config import Settings
from launchkit.core.logging import add_service_context, configure_logging


def test_json_logging_emits_structured_event(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(log_json=True))

    structlog.get_logger().info("backend_started", component="test")

    captured = capsys.readouterr()
    event = json.loads(captured.out)
    assert event["event"] == "backend_started"
    assert event["component"] == "test"
    assert event["level"] == "info"


def test_json_logging_includes_exception_text(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(Settings(log_json=True))

    try:
        raise RuntimeError("vercel token rejected")
    except RuntimeError:
        structlog.get_logger().exception("job_failed", job_id="job_test", kind="deployment.create")

    event = json.loads(capsys.readouterr().out)
    assert event["event"] == "job_failed"
    assert event["kind"] == "deployment.create"
    assert "vercel token rejected" in event["exception"]


def test_service_context_processor() -> None:
    event = add_service_context(None, "info", {"event": "ready"})

    assert event["service"] == "launchkit"
