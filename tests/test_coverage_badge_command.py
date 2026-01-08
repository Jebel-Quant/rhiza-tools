"""Tests for the coverage-badge command."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from rhiza_tools.cli import app
from rhiza_tools.commands.coverage_badge import (
    DEFAULT_BADGE_FILENAME,
    DEFAULT_COVERAGE_JSON,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_THRESHOLDS,
    CoverageBadgeConfig,
    coverage_badge_command,
    extract_coverage_percentage,
    generate_badge_json,
    get_badge_color,
    get_coverage_badge_config,
)

runner = CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory and change to it."""
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp_dir:
        os.chdir(tmp_dir)
        yield Path(tmp_dir)
        os.chdir(original_cwd)


@pytest.fixture
def coverage_json_file(temp_dir):
    """Create a coverage.json file with sample data."""
    coverage_dir = temp_dir / "_tests"
    coverage_dir.mkdir(parents=True)
    coverage_file = coverage_dir / "coverage.json"
    coverage_data = {
        "totals": {
            "percent_covered": 85.5,
            "covered_lines": 171,
            "num_statements": 200,
        }
    }
    with open(coverage_file, "w") as f:
        json.dump(coverage_data, f)
    return coverage_file


@pytest.fixture
def cfg_toml_file(temp_dir):
    """Create a .cfg.toml file with coverage-badge config."""
    rhiza_dir = temp_dir / ".rhiza"
    rhiza_dir.mkdir(parents=True)
    cfg_file = rhiza_dir / ".cfg.toml"
    cfg_content = """
[tool.coverage-badge]
coverage_json = "_custom/coverage.json"
output_dir = "_custom/output"
badge_filename = "my-badge.json"

[tool.coverage-badge.thresholds]
95 = "brightgreen"
85 = "green"
75 = "yellow"
0 = "red"
"""
    with open(cfg_file, "w") as f:
        f.write(cfg_content)
    return cfg_file


class TestGetBadgeColor:
    """Tests for get_badge_color function."""

    def test_brightgreen_for_90_plus(self):
        """Test that 90%+ coverage returns brightgreen."""
        assert get_badge_color(90, DEFAULT_THRESHOLDS) == "brightgreen"
        assert get_badge_color(95, DEFAULT_THRESHOLDS) == "brightgreen"
        assert get_badge_color(100, DEFAULT_THRESHOLDS) == "brightgreen"

    def test_green_for_80_to_89(self):
        """Test that 80-89% coverage returns green."""
        assert get_badge_color(80, DEFAULT_THRESHOLDS) == "green"
        assert get_badge_color(85, DEFAULT_THRESHOLDS) == "green"
        assert get_badge_color(89, DEFAULT_THRESHOLDS) == "green"

    def test_yellowgreen_for_70_to_79(self):
        """Test that 70-79% coverage returns yellowgreen."""
        assert get_badge_color(70, DEFAULT_THRESHOLDS) == "yellowgreen"
        assert get_badge_color(75, DEFAULT_THRESHOLDS) == "yellowgreen"
        assert get_badge_color(79, DEFAULT_THRESHOLDS) == "yellowgreen"

    def test_yellow_for_60_to_69(self):
        """Test that 60-69% coverage returns yellow."""
        assert get_badge_color(60, DEFAULT_THRESHOLDS) == "yellow"
        assert get_badge_color(65, DEFAULT_THRESHOLDS) == "yellow"
        assert get_badge_color(69, DEFAULT_THRESHOLDS) == "yellow"

    def test_orange_for_50_to_59(self):
        """Test that 50-59% coverage returns orange."""
        assert get_badge_color(50, DEFAULT_THRESHOLDS) == "orange"
        assert get_badge_color(55, DEFAULT_THRESHOLDS) == "orange"
        assert get_badge_color(59, DEFAULT_THRESHOLDS) == "orange"

    def test_red_for_below_50(self):
        """Test that below 50% coverage returns red."""
        assert get_badge_color(0, DEFAULT_THRESHOLDS) == "red"
        assert get_badge_color(25, DEFAULT_THRESHOLDS) == "red"
        assert get_badge_color(49, DEFAULT_THRESHOLDS) == "red"

    def test_custom_thresholds(self):
        """Test with custom thresholds."""
        custom_thresholds = {
            95: "brightgreen",
            50: "yellow",
            0: "red",
        }
        assert get_badge_color(95, custom_thresholds) == "brightgreen"
        assert get_badge_color(75, custom_thresholds) == "yellow"
        assert get_badge_color(25, custom_thresholds) == "red"


class TestGenerateBadgeJson:
    """Tests for generate_badge_json function."""

    def test_generates_valid_schema(self):
        """Test that the generated JSON has valid shields.io schema."""
        badge = generate_badge_json(85, "green")
        assert badge["schemaVersion"] == 1
        assert badge["label"] == "coverage"
        assert badge["message"] == "85%"
        assert badge["color"] == "green"

    def test_percentage_formatting(self):
        """Test that percentage is formatted correctly."""
        badge = generate_badge_json(85.7, "green")
        assert badge["message"] == "86%"

        badge = generate_badge_json(0, "red")
        assert badge["message"] == "0%"

        badge = generate_badge_json(100, "brightgreen")
        assert badge["message"] == "100%"


class TestExtractCoveragePercentage:
    """Tests for extract_coverage_percentage function."""

    def test_extracts_percentage(self, coverage_json_file):
        """Test that percentage is extracted correctly."""
        percentage = extract_coverage_percentage(coverage_json_file)
        assert percentage == 85.5

    def test_missing_file_exits_gracefully(self, temp_dir):
        """Test that missing file exits with code 0."""
        with pytest.raises(typer.Exit) as exc_info:
            extract_coverage_percentage(temp_dir / "nonexistent.json")
        assert exc_info.value.exit_code == 0

    def test_invalid_json_exits_with_error(self, temp_dir):
        """Test that invalid JSON exits with code 1."""
        bad_file = temp_dir / "bad.json"
        with open(bad_file, "w") as f:
            f.write("not json")
        with pytest.raises(typer.Exit) as exc_info:
            extract_coverage_percentage(bad_file)
        assert exc_info.value.exit_code == 1

    def test_missing_key_exits_with_error(self, temp_dir):
        """Test that missing key in JSON exits with code 1."""
        bad_file = temp_dir / "incomplete.json"
        with open(bad_file, "w") as f:
            json.dump({"totals": {}}, f)
        with pytest.raises(typer.Exit) as exc_info:
            extract_coverage_percentage(bad_file)
        assert exc_info.value.exit_code == 1


class TestCoverageBadgeConfig:
    """Tests for CoverageBadgeConfig dataclass."""

    def test_badge_path_property(self):
        """Test badge_path property returns correct path."""
        config = CoverageBadgeConfig(
            coverage_json=Path("_tests/coverage.json"),
            output_dir=Path("_book/tests"),
            badge_filename="coverage-badge.json",
            thresholds=DEFAULT_THRESHOLDS,
        )
        assert config.badge_path == Path("_book/tests/coverage-badge.json")


class TestGetCoverageBadgeConfig:
    """Tests for get_coverage_badge_config function."""

    def test_defaults_without_config_file(self, temp_dir):
        """Test that defaults are used when no config file exists."""
        config = get_coverage_badge_config()
        assert config.coverage_json == Path(DEFAULT_COVERAGE_JSON)
        assert config.output_dir == Path(DEFAULT_OUTPUT_DIR)
        assert config.badge_filename == DEFAULT_BADGE_FILENAME
        assert config.thresholds == DEFAULT_THRESHOLDS

    def test_reads_from_config_file(self, cfg_toml_file):
        """Test that config is read from .cfg.toml file."""
        config = get_coverage_badge_config()
        assert config.coverage_json == Path("_custom/coverage.json")
        assert config.output_dir == Path("_custom/output")
        assert config.badge_filename == "my-badge.json"
        assert config.thresholds == {95: "brightgreen", 85: "green", 75: "yellow", 0: "red"}

    def test_overrides_take_precedence(self, cfg_toml_file):
        """Test that explicit overrides take precedence over config file."""
        config = get_coverage_badge_config(
            coverage_json=Path("override/coverage.json"),
            output_dir=Path("override/output"),
            badge_filename="override.json",
        )
        assert config.coverage_json == Path("override/coverage.json")
        assert config.output_dir == Path("override/output")
        assert config.badge_filename == "override.json"


class TestCoverageBadgeCommand:
    """Tests for coverage_badge_command function."""

    def test_generates_badge_file(self, coverage_json_file, temp_dir):
        """Test that badge file is generated correctly."""
        output_dir = temp_dir / "_book" / "tests"
        coverage_badge_command(
            coverage_json=coverage_json_file,
            output_dir=output_dir,
        )

        badge_path = output_dir / "coverage-badge.json"
        assert badge_path.exists()

        with open(badge_path) as f:
            badge = json.load(f)

        assert badge["schemaVersion"] == 1
        assert badge["label"] == "coverage"
        assert badge["message"] == "86%"  # 85.5 rounded
        assert badge["color"] == "green"  # 85% is in green range

    def test_dry_run_does_not_create_file(self, coverage_json_file, temp_dir):
        """Test that dry run does not create any files."""
        output_dir = temp_dir / "_book" / "tests"
        coverage_badge_command(
            coverage_json=coverage_json_file,
            output_dir=output_dir,
            dry_run=True,
        )

        badge_path = output_dir / "coverage-badge.json"
        assert not badge_path.exists()

    def test_creates_output_directory(self, coverage_json_file, temp_dir):
        """Test that output directory is created if it doesn't exist."""
        output_dir = temp_dir / "new" / "nested" / "directory"
        coverage_badge_command(
            coverage_json=coverage_json_file,
            output_dir=output_dir,
        )

        assert output_dir.exists()
        assert (output_dir / "coverage-badge.json").exists()

    def test_custom_badge_filename(self, coverage_json_file, temp_dir):
        """Test custom badge filename."""
        output_dir = temp_dir / "_book" / "tests"
        coverage_badge_command(
            coverage_json=coverage_json_file,
            output_dir=output_dir,
            badge_filename="custom-badge.json",
        )

        assert (output_dir / "custom-badge.json").exists()
        assert not (output_dir / "coverage-badge.json").exists()


class TestCoverageBadgeCLI:
    """Tests for the CLI coverage-badge command."""

    def test_cli_help(self):
        """Test that help output works."""
        result = runner.invoke(app, ["coverage-badge", "--help"])
        assert result.exit_code == 0
        assert "coverage-badge" in result.output
        assert "--coverage-json" in result.output
        assert "--output-dir" in result.output
        assert "--dry-run" in result.output

    def test_cli_dry_run(self, coverage_json_file, temp_dir):
        """Test CLI with dry-run flag."""
        output_dir = temp_dir / "_book" / "tests"
        result = runner.invoke(
            app,
            [
                "coverage-badge",
                "--coverage-json", str(coverage_json_file),
                "--output-dir", str(output_dir),
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Would write badge JSON" in result.output
        assert not (output_dir / "coverage-badge.json").exists()

    def test_cli_generates_badge(self, coverage_json_file, temp_dir):
        """Test CLI generates badge file."""
        output_dir = temp_dir / "_book" / "tests"
        result = runner.invoke(
            app,
            [
                "coverage-badge",
                "--coverage-json", str(coverage_json_file),
                "--output-dir", str(output_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Coverage badge generated" in result.output
        assert (output_dir / "coverage-badge.json").exists()

    def test_cli_missing_coverage_file(self, temp_dir):
        """Test CLI handles missing coverage file gracefully."""
        result = runner.invoke(
            app,
            [
                "coverage-badge",
                "--coverage-json", str(temp_dir / "nonexistent.json"),
            ],
        )
        # Exits with 0 (skip) when file not found
        assert result.exit_code == 0
