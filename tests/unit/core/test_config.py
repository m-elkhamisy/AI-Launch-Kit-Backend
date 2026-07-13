import pytest
from pydantic import ValidationError

from launchkit.core.config import Settings


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.app_name == "AI Launch Kit Backend"
    assert settings.environment == "local"
    assert settings.log_level == "INFO"
    assert settings.log_json is False
    assert settings.openrouter_api_key is None
    assert settings.openrouter_max_concurrent == 2
    assert settings.utility_model is None


def test_settings_read_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAUNCHKIT_ENVIRONMENT", "test")
    monkeypatch.setenv("LAUNCHKIT_LOG_JSON", "true")
    monkeypatch.setenv("LAUNCHKIT_OPENROUTER_API_KEY", "secret")
    monkeypatch.setenv("LAUNCHKIT_OPENROUTER_SEQUENTIAL", "true")

    settings = Settings()

    assert settings.environment == "test"
    assert settings.log_json is True
    assert settings.openrouter_api_key is not None
    assert settings.openrouter_api_key.get_secret_value() == "secret"
    assert settings.openrouter_sequential is True


def test_settings_reject_invalid_log_level() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="verbose")
