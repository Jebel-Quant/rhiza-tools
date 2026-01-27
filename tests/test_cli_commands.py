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
    mock_bump_command.assert_called_once_with("1.0.1", True, False, False, False)

    mock_bump_command.reset_mock()

    result = runner.invoke(app, ["bump", "patch", "--commit", "--allow-dirty", "--verbose"])
    assert result.exit_code == 0
    mock_bump_command.assert_called_once_with("patch", False, True, True, True)


def test_release_command():
    """Test the release command."""
    result = runner.invoke(app, ["release", "--dry-run"])
    assert result.exit_code == 0
    assert "Would create and push release tag" in result.stdout

    result = runner.invoke(app, ["release"])
    assert result.exit_code == 0
    assert "Creating and pushing release tag" in result.stdout


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


def test_check_workflow(monkeypatch):
    """Test the check-workflow command."""
    mock_check_workflow = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.check_workflow_command", mock_check_workflow)

    result = runner.invoke(app, ["check-workflow", "workflow1.yml", "workflow2.yml"])
    assert result.exit_code == 0
    mock_check_workflow.assert_called_once_with(["workflow1.yml", "workflow2.yml"])
