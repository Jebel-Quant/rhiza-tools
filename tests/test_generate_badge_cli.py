"""Unit tests for the generate_coverage_badge CLI command."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from rhiza_tools.cli import app

runner = CliRunner()


class TestGenerateCoverageBadgeCLI:
    """Tests for the generate_coverage_badge CLI command."""

    def test_cli_with_default_arguments(self, tmp_path, monkeypatch):
        """Test CLI command with default arguments."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create default directories and files
        tests_dir = tmp_path / "_tests"
        tests_dir.mkdir()
        coverage_json = tests_dir / "coverage.json"
        coverage_data = {"totals": {"percent_covered": 85.0}}
        coverage_json.write_text(json.dumps(coverage_data))

        # Execute
        result = runner.invoke(app, ["generate-coverage-badge"])

        # Verify
        assert result.exit_code == 0

        # Check output file was created
        badge_json = tmp_path / "_book" / "tests" / "coverage-badge.json"
        assert badge_json.exists()

        badge_data = json.loads(badge_json.read_text())
        assert badge_data["message"] == "85%"
        assert badge_data["color"] == "green"

    def test_cli_with_custom_paths(self, tmp_path, monkeypatch):
        """Test CLI command with custom input and output paths."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create custom directories and files
        custom_input = tmp_path / "custom" / "coverage.json"
        custom_input.parent.mkdir(parents=True)
        coverage_data = {"totals": {"percent_covered": 92.0}}
        custom_input.write_text(json.dumps(coverage_data))

        custom_output = tmp_path / "output" / "my-badge.json"

        # Execute
        result = runner.invoke(
            app,
            [
                "generate-coverage-badge",
                "--coverage-json",
                str(custom_input),
                "--output",
                str(custom_output),
            ],
        )

        # Verify
        assert result.exit_code == 0
        assert custom_output.exists()

        badge_data = json.loads(custom_output.read_text())
        assert badge_data["message"] == "92%"
        assert badge_data["color"] == "brightgreen"

    def test_cli_missing_coverage_json(self, tmp_path, monkeypatch):
        """Test CLI command when coverage.json is missing."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Execute without creating coverage.json
        result = runner.invoke(app, ["generate-coverage-badge"])

        # Should exit successfully with warning (exit code 0)
        assert result.exit_code == 0

    def test_cli_invalid_coverage_json(self, tmp_path, monkeypatch):
        """Test CLI command with invalid JSON file."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create invalid JSON file
        tests_dir = tmp_path / "_tests"
        tests_dir.mkdir()
        coverage_json = tests_dir / "coverage.json"
        coverage_json.write_text("{ invalid json }")

        # Execute
        result = runner.invoke(app, ["generate-coverage-badge"])

        # Should exit with error
        assert result.exit_code == 1

    def test_cli_help_message(self):
        """Test that CLI help message is displayed correctly."""
        result = runner.invoke(app, ["generate-coverage-badge", "--help"])

        assert result.exit_code == 0
        assert "Generate a coverage badge for the project" in result.stdout
        # Check for options - they may have ANSI codes, so check for core text
        # The text "coverage" and "json" are separated by ANSI codes
        assert "coverage" in result.stdout
        assert "json" in result.stdout
        assert "output" in result.stdout
        assert "Path to coverage.json file" in result.stdout

    def test_cli_calls_command_function(self, monkeypatch):
        """Test that CLI correctly calls the underlying command function."""
        # Mock the command function
        mock_command = MagicMock()
        monkeypatch.setattr("rhiza_tools.cli.generate_coverage_badge_command", mock_command)

        # Execute with default args
        result = runner.invoke(app, ["generate-coverage-badge"])

        # Verify the mock was called
        assert result.exit_code == 0
        mock_command.assert_called_once()

        # Verify the arguments passed
        call_args = mock_command.call_args
        assert call_args.kwargs["coverage_json_path"] == Path("_tests/coverage.json")
        assert call_args.kwargs["output_path"] == Path("_book/tests/coverage-badge.json")

    def test_cli_calls_command_with_custom_args(self, monkeypatch):
        """Test that CLI correctly passes custom arguments to command function."""
        # Mock the command function
        mock_command = MagicMock()
        monkeypatch.setattr("rhiza_tools.cli.generate_coverage_badge_command", mock_command)

        # Execute with custom args
        result = runner.invoke(
            app,
            [
                "generate-coverage-badge",
                "--coverage-json",
                "/custom/path.json",
                "--output",
                "/custom/output.json",
            ],
        )

        # Verify the mock was called
        assert result.exit_code == 0
        mock_command.assert_called_once()

        # Verify the arguments passed
        call_args = mock_command.call_args
        assert call_args.kwargs["coverage_json_path"] == Path("/custom/path.json")
        assert call_args.kwargs["output_path"] == Path("/custom/output.json")

    def test_cli_relative_paths(self, tmp_path, monkeypatch):
        """Test CLI with relative paths."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create coverage file
        coverage_json = tmp_path / "coverage.json"
        coverage_data = {"totals": {"percent_covered": 75.0}}
        coverage_json.write_text(json.dumps(coverage_data))

        # Execute with relative paths
        result = runner.invoke(
            app,
            [
                "generate-coverage-badge",
                "--coverage-json",
                "coverage.json",
                "--output",
                "badge.json",
            ],
        )

        # Verify
        assert result.exit_code == 0
        badge_json = tmp_path / "badge.json"
        assert badge_json.exists()

        badge_data = json.loads(badge_json.read_text())
        assert badge_data["message"] == "75%"

    def test_cli_output_to_stdout(self, tmp_path, monkeypatch):
        """Test that CLI command outputs informational messages."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create coverage file
        tests_dir = tmp_path / "_tests"
        tests_dir.mkdir()
        coverage_json = tests_dir / "coverage.json"
        coverage_data = {"totals": {"percent_covered": 88.5}}
        coverage_json.write_text(json.dumps(coverage_data))

        # Execute
        result = runner.invoke(app, ["generate-coverage-badge"])

        # Verify informational output
        assert result.exit_code == 0
        assert "[INFO]" in result.stdout or "[INFO]" in result.stderr

    def test_cli_handles_permission_error(self, tmp_path, monkeypatch):
        """Test CLI handles permission errors gracefully."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create coverage file
        tests_dir = tmp_path / "_tests"
        tests_dir.mkdir()
        coverage_json = tests_dir / "coverage.json"
        coverage_data = {"totals": {"percent_covered": 85.0}}
        coverage_json.write_text(json.dumps(coverage_data))

        # Patch the generate_coverage_badge_command to raise PermissionError
        def mock_command(*args, **kwargs):
            raise PermissionError("Permission denied")  # noqa: TRY003

        with patch("rhiza_tools.cli.generate_coverage_badge_command", mock_command):
            result = runner.invoke(app, ["generate-coverage-badge"])

            # Should propagate the error
            assert result.exit_code != 0
            assert result.exception is not None

    def test_cli_creates_nested_output_directories(self, tmp_path, monkeypatch):
        """Test that CLI creates nested output directories."""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Create coverage file
        coverage_json = tmp_path / "coverage.json"
        coverage_data = {"totals": {"percent_covered": 80.0}}
        coverage_json.write_text(json.dumps(coverage_data))

        # Execute with deeply nested output path
        nested_output = "deeply/nested/path/to/badge.json"
        result = runner.invoke(
            app,
            [
                "generate-coverage-badge",
                "--coverage-json",
                "coverage.json",
                "--output",
                nested_output,
            ],
        )

        # Verify
        assert result.exit_code == 0
        assert (tmp_path / nested_output).exists()
