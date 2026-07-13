"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
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
    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    site_url: str = "http://localhost:8000"
    openrouter_app_title: str = "LaunchKit Generator"
    generation_model: str = "anthropic/claude-sonnet-5"
    utility_model: str | None = None
    image_model: str = "google/gemini-2.5-flash-image"
    pexels_api_key: SecretStr | None = None
    pexels_base_url: str = "https://api.pexels.com/v1"
    openrouter_max_concurrent: int = Field(default=2, ge=1)
    openrouter_min_request_gap_ms: int = Field(default=250, ge=0)
    openrouter_sequential: bool = False
    openrouter_retry_attempts: int = Field(default=6, ge=1)
    v0_api_key: SecretStr | None = None
    v0_base_url: str = "https://api.v0.dev/v1"
    v0_model: str = "v0-max"
    local_data_dir: Path = Path("local_data")
    s3_bucket: str | None = None
    s3_prefix: str = "submissions/"
    aws_region: str = "me-central-1"


@lru_cache
def get_settings() -> Settings:
    """Return one settings instance per process."""

    return Settings()
