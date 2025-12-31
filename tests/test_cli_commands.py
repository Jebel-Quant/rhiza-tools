"""Tests for CLI commands in rhiza_tools.cli.py."""

from unittest.mock import MagicMock

from typer.testing import CliRunner

from rhiza_tools.cli import app

runner = CliRunner()


def test_bump_command(monkeypatch):
    """Test the bump command."""
    mock_logger = MagicMock()
    monkeypatch.setattr("rhiza_tools.commands.bump.logger", mock_logger)

    with runner.isolated_filesystem():
        with open("pyproject.toml", "w") as f:
            f.write('[project]\nname = "test"\nversion = "1.0.0"\n')

        result = runner.invoke(app, ["bump", "1.0.1", "--dry-run"])
        assert result.exit_code == 0

        assert any("New version will be: 1.0.1" in str(call) for call in mock_logger.info.mock_calls)
        assert any("Dry run enabled. Skipping actual changes." in str(call) for call in mock_logger.info.mock_calls)

        mock_logger.reset_mock()

        result = runner.invoke(app, ["bump", "1.0.1"])
        assert result.exit_code == 0
        assert any("New version will be: 1.0.1" in str(call) for call in mock_logger.info.mock_calls)
        assert any("Updating pyproject.toml..." in str(call) for call in mock_logger.info.mock_calls)
        assert any(
            "Version bumped: 1.0.0 -> 1.0.1 in pyproject.toml" in str(call) for call in mock_logger.success.mock_calls
        )


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
