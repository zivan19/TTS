"""Configuration helpers for the FastAPI server."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration."""

    data_dir: Path = Field(default_factory=lambda: Path("data"))
    jobs_subdir: str = Field(default="jobs")
    ui_title: str = Field(default="TTS Demo Workbench")

    class Config:
        env_prefix = "tts_"
        env_file = ".env"

    @property
    def jobs_dir(self) -> Path:
        base = self.data_dir / self.jobs_subdir
        base.mkdir(parents=True, exist_ok=True)
        return base


@lru_cache()
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
