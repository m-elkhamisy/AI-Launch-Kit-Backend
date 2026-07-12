import pytest
from pydantic import ValidationError

from launchkit.core.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.app_name == "AI Launch Kit Backend"
    assert settings.environment == "local"
    assert settings.log_level == "INFO"
    assert settings.log_json is False


def test_settings_read_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAUNCHKIT_ENVIRONMENT", "test")
    monkeypatch.setenv("LAUNCHKIT_LOG_JSON", "true")

    settings = Settings()

    assert settings.environment == "test"
    assert settings.log_json is True


def test_settings_reject_invalid_log_level() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="verbose")
