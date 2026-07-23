from functools import lru_cache
from pathlib import Path
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
    raw_snapshot_path: Path = Path("../../data/raw")
    raw_snapshot_retention_hours: int = 6
    static_gtfs_url: str = "https://cdn.mbta.com/MBTA_GTFS.zip"
    vehicle_positions_url: str = "https://cdn.mbta.com/realtime/VehiclePositions.pb"
    trip_updates_url: str = "https://cdn.mbta.com/realtime/TripUpdates.pb"
    alerts_url: str = "https://cdn.mbta.com/realtime/Alerts.pb"
    allowed_origins: tuple[str, ...] = ("http://localhost:3000",)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
