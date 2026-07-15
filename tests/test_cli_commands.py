"""Tests for CLI commands in rhiza_tools.cli.py."""

from unittest.mock import MagicMock, patch

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


def test_release_command(monkeypatch):
    """Test the release command."""
    mock_release_command = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.release_command", mock_release_command)

    result = runner.invoke(app, ["release", "--dry-run"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, language, config, allow_older)
    mock_release_command.assert_called_once_with(None, False, True, False, None, None, False)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, language, config, allow_older)
    mock_release_command.assert_called_once_with(None, False, False, False, None, None, False)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release", "--non-interactive"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, language, config, allow_older)
    mock_release_command.assert_called_once_with(None, False, False, True, None, None, False)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release", "--bump", "MINOR", "--push", "--dry-run"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, language, config, allow_older)
    mock_release_command.assert_called_once_with("MINOR", True, True, False, None, None, False)

    mock_release_command.reset_mock()

    from rhiza_tools.commands.bump import Language

    result = runner.invoke(app, ["release", "--language", "go", "--dry-run"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, language, config, allow_older)
    mock_release_command.assert_called_once_with(None, False, True, False, Language.GO, None, False)

    mock_release_command.reset_mock()

    result = runner.invoke(app, ["release", "--language", "invalid"])
    assert result.exit_code == 1
    assert "Invalid language: invalid" in result.output
    assert "Supported languages: python, go" in result.output

    mock_release_command.reset_mock()

    from pathlib import Path

    result = runner.invoke(app, ["release", "--config", "/custom/.cfg.toml", "--dry-run"])
    assert result.exit_code == 0
    # release_command(bump, push, dry_run, non_interactive, language, config, allow_older)
    mock_release_command.assert_called_once_with(None, False, True, False, None, Path("/custom/.cfg.toml"), False)


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


# ---------------------------------------------------------------------------
# Branch coverage relocated from the former test_coverage_100.py
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for uncovered branches in cli.py."""

    def test_apply_verbose_true(self):
        """cli.py:62 – configure_console called with verbose=True."""
        from rhiza_tools.cli import _apply_verbose

        with patch("rhiza_tools.cli.configure_console") as mock_configure:
            _apply_verbose(True)
            mock_configure.assert_called_once_with(verbose=True)

    def test_release_invalid_language(self):
        """cli.py:272-276 – invalid language in release exits with code 1."""
        result = runner.invoke(app, ["release", "--language", "ruby"])
        assert result.exit_code == 1

    def test_analyze_benchmarks_cli(self, monkeypatch):
        """cli.py:459-460 – analyze-benchmarks command invokes analyze_benchmarks_command."""
        mock_cmd = MagicMock()
        monkeypatch.setattr("rhiza_tools.cli.analyze_benchmarks_command", mock_cmd)
        result = runner.invoke(app, ["analyze-benchmarks"])
        assert result.exit_code == 0
        mock_cmd.assert_called_once()

    def test_analyze_benchmarks_cli_verbose(self, monkeypatch):
        """cli.py:459 – _apply_verbose is triggered for analyze-benchmarks --verbose."""
        mock_cmd = MagicMock()
        monkeypatch.setattr("rhiza_tools.cli.analyze_benchmarks_command", mock_cmd)
        result = runner.invoke(app, ["analyze-benchmarks", "--verbose"])
        assert result.exit_code == 0
