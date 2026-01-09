"""Configuration management for rhiza-tools."""

from pathlib import Path
from typing import Any

import tomlkit
from loguru import logger

CONFIG_FILENAME = ".rhiza/.cfg.toml"


class RhizaConfig:
    """Rhiza tools configuration."""

    def __init__(self, config_path: Path | None = None):
        """Initialize RhizaConfig."""
        self.config_path = config_path or Path(CONFIG_FILENAME)
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            logger.debug(f"Configuration file {self.config_path} not found.")
            return

        try:
            with open(self.config_path) as f:
                self._data = tomlkit.parse(f.read())
        except Exception as e:
            logger.error(f"Failed to parse configuration file {self.config_path}: {e}")
            raise

    @property
    def bumpversion(self) -> dict[str, Any]:
        """Get bumpversion configuration."""
        return self._data.get("tool", {}).get("bumpversion", {})

    @property
    def generate_badges(self) -> dict[str, Any]:
        """Get generate-badges configuration."""
        return self._data.get("tool", {}).get("generate-badges", {})

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._data.get(key, default)


def load_config(path: Path | None = None) -> RhizaConfig:
    """Load configuration."""
    return RhizaConfig(path)
