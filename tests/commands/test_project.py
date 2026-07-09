"""Tests for rhiza_tools.commands._project."""

import pytest
import typer


class TestProject:
    """Tests for uncovered branches in commands/_project.py."""

    def test_get_current_version_success(self, tmp_path, monkeypatch):
        """get_current_version returns the version string from a valid pyproject.toml."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\nversion = '1.2.3'\n")
        from rhiza_tools.commands._project import get_current_version

        assert get_current_version() == "1.2.3"

    def test_get_current_version_exception(self, tmp_path, monkeypatch):
        """get_current_version exits when pyproject.toml cannot be parsed."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[invalid toml [[[")
        from rhiza_tools.commands._project import get_current_version

        with pytest.raises(typer.Exit):
            get_current_version()
