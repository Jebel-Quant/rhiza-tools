"""Tests for rhiza_tools.config."""

from pathlib import Path

import pytest
import tomlkit

from rhiza_tools.config import CONFIG_FILENAME, RhizaConfig


def test_load_config_valid(tmp_path):
    """Test loading a valid configuration file."""
    config_file = tmp_path / CONFIG_FILENAME
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_content = """
[tool.bumpversion]
current_version = "1.0.0"
"""
    config_file.write_text(config_content)
    
    config = RhizaConfig(config_path=config_file)
    assert config.bumpversion["current_version"] == "1.0.0"

def test_load_config_missing(tmp_path):
    """Test loading a missing configuration file."""
    config_file = tmp_path / "nonexistent.toml"
    config = RhizaConfig(config_path=config_file)
    assert config._data == {}
    assert config.bumpversion == {}

def test_load_config_invalid_toml(tmp_path):
    """Test loading an invalid configuration file."""
    config_file = tmp_path / CONFIG_FILENAME
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("invalid toml [")
    
    with pytest.raises(tomlkit.exceptions.ParseError):
        RhizaConfig(config_path=config_file)

def test_get_value(tmp_path):
    """Test getting a value from configuration."""
    config_file = tmp_path / CONFIG_FILENAME
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_content = """
key = "value"
"""
    config_file.write_text(config_content)
    
    config = RhizaConfig(config_path=config_file)
    assert config.get("key") == "value"
    assert config.get("missing", "default") == "default"
