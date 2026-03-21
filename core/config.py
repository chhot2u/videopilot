"""VideoPilot — Global configuration using Pydantic Settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class VideoPilotConfig(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    model_config = {"env_prefix": "VIDEOPILOT_", "env_file": ".env", "extra": "ignore"}

    # General
    env: Literal["development", "production", "testing"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    temp_dir: Path = Path("/tmp/videopilot")
    output_dir: Path = Path("./output")
    max_file_size_mb: int = 2000

    # Model settings
    models_dir: Path = Path("./models/weights")
    device: Literal["cpu", "cuda", "mps"] = "cpu"
    max_ram_gb: float = 12.0

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 2
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    def ensure_dirs(self) -> None:
        """Create required directories if they don't exist."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)


# Singleton config instance
_config: VideoPilotConfig | None = None


def get_config() -> VideoPilotConfig:
    """Get or create the global configuration instance."""
    global _config
    if _config is None:
        _config = VideoPilotConfig()
        _config.ensure_dirs()
    return _config
