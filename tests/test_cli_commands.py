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
    mock_bump_command = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.bump_command", mock_bump_command)

    result = runner.invoke(app, ["bump", "1.0.1", "--dry-run"])
    assert result.exit_code == 0
    # bump_command(version, dry_run, commit, push, branch, allow_dirty, verbose)
    mock_bump_command.assert_called_once_with("1.0.1", True, False, False, None, False, False)

    mock_bump_command.reset_mock()

    result = runner.invoke(app, ["bump", "patch", "--commit", "--allow-dirty", "--verbose"])
    assert result.exit_code == 0
    # bump_command(version, dry_run, commit, push, branch, allow_dirty, verbose)
    mock_bump_command.assert_called_once_with("patch", False, True, False, None, True, True)


def test_release_command(monkeypatch):
    """Test the release command."""
    mock_release_command = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.release_command", mock_release_command)

    result = runner.invoke(app, ["release", "--dry-run"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive)
    mock_release_command.assert_called_once_with(None, False, True, False)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive)
    mock_release_command.assert_called_once_with(None, False, False, False)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release", "--non-interactive"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive)
    mock_release_command.assert_called_once_with(None, False, False, True)


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
