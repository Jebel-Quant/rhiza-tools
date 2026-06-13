"""Tests for rhiza_tools.commands._shared."""

import pytest
import typer


class TestShared:
    """Tests for uncovered branches in commands/_shared.py."""

    def test_get_current_version_success(self, tmp_path, monkeypatch):
        """_shared.py:81-82 – returns version string from valid pyproject.toml."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\nversion = '1.2.3'\n")
        from rhiza_tools.commands._shared import get_current_version

        assert get_current_version() == "1.2.3"

    def test_get_current_version_exception(self, tmp_path, monkeypatch):
        """_shared.py:83-85 – exits when pyproject.toml cannot be parsed."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[invalid toml [[[")
        from rhiza_tools.commands._shared import get_current_version

        with pytest.raises(typer.Exit):
            get_current_version()
