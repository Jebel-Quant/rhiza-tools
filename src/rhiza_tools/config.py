"""Configuration management for rhiza-tools."""

from pathlib import Path
from typing import Any, Dict, Optional

import tomlkit
from loguru import logger

CONFIG_FILENAME = ".rhiza/.cfg.toml"

class RhizaConfig:
    """Rhiza tools configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(CONFIG_FILENAME)
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            logger.debug(f"Configuration file {self.config_path} not found.")
            return

        try:
            with open(self.config_path, "r") as f:
                self._data = tomlkit.parse(f.read())
        except Exception as e:
            logger.error(f"Failed to parse configuration file {self.config_path}: {e}")
            raise

    @property
    def bumpversion(self) -> Dict[str, Any]:
        """Get bumpversion configuration."""
        return self._data.get("tool", {}).get("bumpversion", {})

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._data.get(key, default)

def load_config(path: Optional[Path] = None) -> RhizaConfig:
    """Load configuration."""
    return RhizaConfig(path)
