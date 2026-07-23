from functools import lru_cache
from typing import Literal

from pydantic import RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TP_",
        extra="ignore",
    )

    environment: Literal["development", "test", "preview", "production"] = "development"
    database_url: str | None = None
    redis_url: RedisDsn | None = None
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
