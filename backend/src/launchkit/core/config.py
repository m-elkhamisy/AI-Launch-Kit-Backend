"""Environment-backed application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]


class Settings(BaseSettings):
    """Runtime settings loaded from ``LAUNCHKIT_`` environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LAUNCHKIT_",
        extra="ignore",
    )

    app_name: str = "AI Launch Kit Backend"
    environment: Environment = "local"
    debug: bool = False
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_json: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return one settings instance per process."""

    return Settings()
