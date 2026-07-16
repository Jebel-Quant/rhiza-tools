"""Unit tests for the version-matrix command (classifier-based)."""

import json

import pytest
import typer

from rhiza_tools.commands.version_matrix import (
    PyProjectError,
    get_supported_versions,
    version_matrix_command,
)

_PYPROJECT_311_312 = """
[project]
name = "test-project"
requires-python = ">=3.11"
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3 :: Only",
    "License :: OSI Approved :: MIT License",
]
"""


class TestGetSupportedVersions:
    """Tests for the get_supported_versions function."""

    def test_extracts_minor_versions_from_classifiers(self, tmp_path):
        """Only concrete major.minor classifiers become matrix entries."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(_PYPROJECT_311_312)

        # "3" and "3 :: Only" are excluded; the license classifier is ignored.
        assert get_supported_versions(pyproject) == ["3.11", "3.12"]

    def test_versions_sorted_semantically_and_deduplicated(self, tmp_path):
        """Versions sort by semver (3.9 < 3.11), and duplicates collapse."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
classifiers = [
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]
""")

        # String sort would put "3.10"/"3.11" before "3.9"; semver sort does not.
        assert get_supported_versions(pyproject) == ["3.9", "3.10", "3.11"]

    def test_missing_pyproject_file(self, tmp_path):
        """Missing pyproject.toml raises PyProjectError."""
        with pytest.raises(PyProjectError) as exc_info:
            get_supported_versions(tmp_path / "nonexistent.toml")
        assert "not found" in str(exc_info.value)

    def test_no_python_classifiers(self, tmp_path):
        """A project without Python classifiers raises PyProjectError."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=3.11"
classifiers = ["License :: OSI Approved :: MIT License"]
""")

        with pytest.raises(PyProjectError) as exc_info:
            get_supported_versions(pyproject)
        assert "no 'Programming Language :: Python :: X.Y' classifiers" in str(exc_info.value)

    def test_missing_classifiers_key(self, tmp_path):
        """A project with no classifiers key at all raises PyProjectError."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
""")

        with pytest.raises(PyProjectError):
            get_supported_versions(pyproject)


class TestVersionMatrixCommand:
    """Tests for the version_matrix_command function."""

    def test_successful_execution_with_defaults(self, tmp_path, monkeypatch, capsys):
        """Default path reads ./pyproject.toml and prints the JSON array."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(_PYPROJECT_311_312)
        monkeypatch.chdir(tmp_path)

        version_matrix_command()

        result = json.loads(capsys.readouterr().out.strip())
        assert result == ["3.11", "3.12"]

    def test_execution_with_custom_pyproject_path(self, tmp_path, capsys):
        """A custom pyproject path is honored."""
        pyproject = tmp_path / "custom" / "pyproject.toml"
        pyproject.parent.mkdir()
        pyproject.write_text(_PYPROJECT_311_312)

        version_matrix_command(pyproject_path=pyproject)

        result = json.loads(capsys.readouterr().out.strip())
        assert result == ["3.11", "3.12"]

    def test_execution_with_missing_file_exits(self, tmp_path, monkeypatch, capsys):
        """A missing pyproject.toml exits with code 1."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(typer.Exit) as exc_info:
            version_matrix_command()

        assert exc_info.value.exit_code == 1
        assert "not found" in capsys.readouterr().err

    def test_execution_with_no_classifiers_exits(self, tmp_path, monkeypatch, capsys):
        """A project without Python classifiers exits with code 1."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
""")
        monkeypatch.chdir(tmp_path)

        with pytest.raises(typer.Exit) as exc_info:
            version_matrix_command()

        assert exc_info.value.exit_code == 1
        assert "classifiers" in capsys.readouterr().err
