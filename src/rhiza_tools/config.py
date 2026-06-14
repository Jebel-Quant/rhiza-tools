"""Configuration management for rhiza-tools.

This module provides configuration loading and access for rhiza-tools.
It reads configuration from a TOML file and provides convenient access
to tool-specific settings.

Example:
    Load configuration from default path::

        from rhiza_tools.config import load_config

        config = load_config()
        bumpversion_config = config.bumpversion

    Load configuration from custom path::

        from pathlib import Path
        from rhiza_tools.config import load_config

        config = load_config(Path("custom/.cfg.toml"))
        value = config.get("custom_key", "default_value")
"""

from pathlib import Path
from typing import Any

import tomlkit
import tomlkit.exceptions
from loguru import logger

from rhiza_tools import console

CONFIG_FILENAME = ".rhiza/.cfg.toml"


class RhizaConfig:
    """Rhiza tools configuration.

    Manages loading and accessing configuration from a TOML file. Provides
    convenient access to tool-specific configuration sections.

    Attributes:
        config_path: Path to the configuration TOML file.

    Example:
        Basic usage::

            config = RhizaConfig()
            bumpversion = config.bumpversion
            custom_value = config.get("my_key", "default")

        With custom path::

            config = RhizaConfig(Path("custom/.cfg.toml"))
            config.load()
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize RhizaConfig.

        Args:
            config_path: Path to the configuration file. If None, uses the
                default path defined in CONFIG_FILENAME.
        """
        self.config_path = config_path or Path(CONFIG_FILENAME)
        self._data: tomlkit.TOMLDocument = tomlkit.TOMLDocument()
        self.load()

    def load(self) -> None:
        """Load configuration from file.

        Reads and parses the TOML configuration file. If the file doesn't exist,
        the configuration will be empty. Logs errors if parsing fails.

        Raises:
            tomlkit.exceptions.ParseError: If the configuration file exists but contains invalid TOML.
            OSError: If the configuration file cannot be read.

        Example:
            config = RhizaConfig(Path("custom/.cfg.toml"))
            config.load()
        """
        if not self.config_path.exists():
            logger.debug(f"Configuration file {self.config_path} not found.")
            return

        try:
            with open(self.config_path) as f:
                self._data = tomlkit.parse(f.read())
        except (tomlkit.exceptions.ParseError, OSError) as e:
            console.error(f"Failed to parse configuration file {self.config_path}: {e}")
            raise

    @property
    # Returns the raw ``[tool.bumpversion]`` TOML sub-table. Its keys and value
    # types are user-defined and open-ended (strings, bools, lists, nested
    # tables), so ``dict[str, Any]`` is the honest type for this passthrough —
    # the strongly-typed bump path uses bump-my-version's own ``Config`` model.
    def bumpversion(self) -> dict[str, Any]:
        """Get bumpversion configuration.

        Returns:
            Dictionary containing bumpversion-specific configuration from the
            [tool.bumpversion] section of the configuration file.

        Example:
            config = RhizaConfig()
            bv_config = config.bumpversion
            print(bv_config.get("current_version"))
        """
        result: dict[str, Any] = self._data.get("tool", {}).get("bumpversion", {})
        return result

    # Generic accessor over arbitrary top-level TOML keys; the value type is
    # only known to the caller, so ``Any`` is intentional here (TOML passthrough).
    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """Get configuration value.

        Args:
            key: Configuration key to retrieve.
            default: Default value to return if key is not found.

        Returns:
            The configuration value for the given key, or default if not found.

        Example:
            config = RhizaConfig()
            value = config.get("custom_setting", "default_value")
        """
        return self._data.get(key, default)


def load_config(path: Path | None = None) -> RhizaConfig:
    """Load configuration.

    Convenience function to create and load a RhizaConfig instance.

    Args:
        path: Path to the configuration file. If None, uses the default path.

    Returns:
        A RhizaConfig instance with the configuration loaded.

    Example:
        Load default configuration::

            config = load_config()

        Load from custom path::

            from pathlib import Path
            config = load_config(Path("custom/.cfg.toml"))
    """
    return RhizaConfig(path)
