"""Pytest configuration and fixtures for rhiza_tools tests."""

import os
import tempfile
from pathlib import Path

import pytest
import tomlkit


@pytest.fixture
def temp_project():
    """Create a temporary project with a pyproject.toml file."""
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.chdir(tmp_dir)

        # Create a basic pyproject.toml
        pyproject_content = {
            "project": {
                "name": "test-project",
                "version": "0.1.0",
                "description": "A test project",
            }
        }

        with open("pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(pyproject_content))

        yield Path(tmp_dir)

        os.chdir(original_cwd)
