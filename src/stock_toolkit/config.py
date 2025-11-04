"""Application configuration using Pydantic settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import DirectoryPath, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="STOCK_TOOLKIT_", extra="ignore"
    )

    data_dir: DirectoryPath | Path = Field(
        default=Path("data"), description="Directorio base de datos"
    )
    cache_dir: Path = Field(
        default=Path("data") / "cache", description="Carpeta para caché temporal"
    )
    default_provider: str = Field(default="yahoo", description="Proveedor por defecto")
    alphavantage_api_key: str | None = Field(default=None, alias="ALPHAVANTAGE_API_KEY")
    max_workers: int = Field(default=4, description="Número máximo de hilos para descargas concurrentes")

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
