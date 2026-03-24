"""Tests for CLI commands in rhiza_tools.cli.py."""

from unittest.mock import MagicMock

from typer.testing import CliRunner

from rhiza_tools import __version__
from rhiza_tools.cli import app

runner = CliRunner()


def test_version_flag():
    """Test the --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "rhiza-tools version" in result.stdout
    # Check that it displays the actual version from the package
    assert __version__ in result.stdout


def test_bump_command(monkeypatch):
    """Test the bump command."""
    from rhiza_tools.commands.bump import BumpOptions

    mock_bump_command = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.bump_command", mock_bump_command)

    result = runner.invoke(app, ["bump", "1.0.1", "--dry-run"])
    assert result.exit_code == 0
    # bump_command should be called with a BumpOptions object
    assert mock_bump_command.call_count == 1
    options = mock_bump_command.call_args[0][0]
    assert isinstance(options, BumpOptions)
    assert options.version == "1.0.1"
    assert options.dry_run is True
    assert options.commit is False
    assert options.push is False
    assert options.branch is None
    assert options.allow_dirty is False

    mock_bump_command.reset_mock()

    result = runner.invoke(app, ["bump", "patch", "--commit", "--allow-dirty"])
    assert result.exit_code == 0
    # bump_command should be called with a BumpOptions object
    assert mock_bump_command.call_count == 1
    options = mock_bump_command.call_args[0][0]
    assert isinstance(options, BumpOptions)
    assert options.version == "patch"
    assert options.dry_run is False
    assert options.commit is True
    assert options.push is False
    assert options.branch is None
    assert options.allow_dirty is True


def test_release_command(monkeypatch):
    """Test the release command."""
    mock_release_command = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.release_command", mock_release_command)

    result = runner.invoke(app, ["release", "--dry-run"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, with_bump, language, config)
    mock_release_command.assert_called_once_with(None, False, True, False, False, None, None)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, with_bump, language, config)
    mock_release_command.assert_called_once_with(None, False, False, False, False, None, None)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release", "--non-interactive"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, with_bump, language, config)
    mock_release_command.assert_called_once_with(None, False, False, True, False, None, None)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release", "--with-bump", "--push", "--dry-run"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, with_bump, language, config)
    mock_release_command.assert_called_once_with(None, True, True, False, True, None, None)

    mock_release_command.reset_mock()

    from rhiza_tools.commands.bump import Language

    result = runner.invoke(app, ["release", "--language", "go", "--dry-run"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, with_bump, language, config)
    mock_release_command.assert_called_once_with(None, False, True, False, False, Language.GO, None)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release", "--language", "invalid"])
    assert result.exit_code == 1
    assert "Invalid language: invalid" in result.output
    assert "Supported languages: python, go" in result.output

    mock_release_command.reset_mock()

    from pathlib import Path

    result = runner.invoke(app, ["release", "--config", "/custom/.cfg.toml", "--dry-run"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, with_bump, language, config)
    mock_release_command.assert_called_once_with(None, False, True, False, False, None, Path("/custom/.cfg.toml"))


def test_update_readme(monkeypatch):
    """Test the update-readme command."""
    # Mock the command function to avoid actual file operations
    mock_update_readme = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.update_readme_command", mock_update_readme)

    result = runner.invoke(app, ["update-readme", "--dry-run"])
    assert result.exit_code == 0
    mock_update_readme.assert_called_once_with(True)

    mock_update_readme.reset_mock()

    result = runner.invoke(app, ["update-readme"])
    assert result.exit_code == 0
    mock_update_readme.assert_called_once_with(False)


def test_version_matrix_command_no_candidates(monkeypatch, tmp_path):
    """Test the version-matrix command with default candidates."""
    # Create a temporary pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=3.11"
""")

    # Mock the command function
    mock_version_matrix = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.version_matrix_command", mock_version_matrix)

    result = runner.invoke(app, ["version-matrix", "--pyproject", str(pyproject)])
    assert result.exit_code == 0
    mock_version_matrix.assert_called_once_with(pyproject_path=pyproject, candidates=None)


def test_version_matrix_command_with_candidates(monkeypatch, tmp_path):
    """Test the version-matrix command with custom candidates."""
    # Create a temporary pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-project"
requires-python = ">=3.11"
""")

    # Mock the command function
    mock_version_matrix = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.version_matrix_command", mock_version_matrix)

    result = runner.invoke(app, ["version-matrix", "--pyproject", str(pyproject), "--candidates", "3.10,3.11,3.12"])
    assert result.exit_code == 0
    mock_version_matrix.assert_called_once_with(pyproject_path=pyproject, candidates=["3.10", "3.11", "3.12"])
