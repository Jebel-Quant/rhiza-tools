"""Tests for CLI commands in rhiza_tools.cli.py."""

from typer.testing import CliRunner

from rhiza_tools.cli import app

runner = CliRunner()


def test_bump_command():
    """Test the bump command."""
    result = runner.invoke(app, ["bump", "1.0.1", "--dry-run"])
    assert result.exit_code == 0
    assert "Would bump version to: 1.0.1" in result.stdout

    result = runner.invoke(app, ["bump", "1.0.1"])
    assert result.exit_code == 0
    assert "Bumping version to: 1.0.1" in result.stdout


def test_release_command():
    """Test the release command."""
    result = runner.invoke(app, ["release", "--dry-run"])
    assert result.exit_code == 0
    assert "Would create and push release tag" in result.stdout

    result = runner.invoke(app, ["release"])
    assert result.exit_code == 0
    assert "Creating and pushing release tag" in result.stdout


def test_update_readme_help_command():
    """Test the update-readme-help command."""
    result = runner.invoke(app, ["update-readme-help", "--dry-run"])
    assert result.exit_code == 0
    assert "Would update README.md with make help output" in result.stdout

    result = runner.invoke(app, ["update-readme-help"])
    assert result.exit_code == 0
    assert "Updating README.md with make help output" in result.stdout
