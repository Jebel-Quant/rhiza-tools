"""Tests covering gaps in release command helper functions."""

from unittest.mock import MagicMock, patch

import pytest
import typer

from rhiza_tools.commands.bump import Language
from rhiza_tools.commands.release import (
    _resolve_explicit_bump_type,
    _resolve_interactive_prompt,
)


def test_resolve_explicit_bump_type_invalid_semver():
    """Test _resolve_explicit_bump_type raises Exit when current version is not valid semver."""
    with (
        patch("rhiza_tools.commands.release.get_current_version", return_value="not-a-semver"),
        pytest.raises(typer.Exit),
    ):
        _resolve_explicit_bump_type("MINOR", Language.PYTHON)


def test_resolve_explicit_bump_type_invalid_bump_type():
    """Test _resolve_explicit_bump_type raises Exit when bump type is unrecognized."""
    with (
        patch("rhiza_tools.commands.release.get_current_version", return_value="1.0.0"),
        pytest.raises(typer.Exit),
    ):
        _resolve_explicit_bump_type("INVALID", Language.PYTHON)


def test_resolve_interactive_prompt_user_declines():
    """Test _resolve_interactive_prompt returns (False, None) when user declines bump."""
    mock_confirm = MagicMock()
    mock_confirm.ask.return_value = False

    with patch("questionary.confirm", return_value=mock_confirm):
        result = _resolve_interactive_prompt(Language.PYTHON)

    assert result == (False, None)


def test_resolve_interactive_prompt_bump_eof():
    """Test _resolve_interactive_prompt returns (False, None) on EOFError."""
    mock_confirm = MagicMock()
    mock_confirm.ask.side_effect = EOFError

    with patch("questionary.confirm", return_value=mock_confirm):
        result = _resolve_interactive_prompt(Language.PYTHON)

    assert result == (False, None)


def test_resolve_interactive_prompt_bump_success():
    """Test _resolve_interactive_prompt returns (True, new_version) when user accepts."""
    mock_confirm = MagicMock()
    mock_confirm.ask.return_value = True

    with (
        patch("questionary.confirm", return_value=mock_confirm),
        patch("rhiza_tools.commands.release.get_current_version", return_value="1.0.0"),
        patch("rhiza_tools.commands.release.get_interactive_bump_type", return_value="1.1.0"),
    ):
        result = _resolve_interactive_prompt(Language.PYTHON)

    assert result == (True, "1.1.0")
