"""Tests for the generate-badges command."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import tomlkit
from typer.testing import CliRunner

from rhiza_tools.cli import app
from rhiza_tools.commands.generate_badges import (
    DEFAULT_COVERAGE_THRESHOLDS,
    BadgeType,
    generate_badges_command,
    generate_codefactor_badge,
    generate_coverage_badge,
    generate_downloads_badge,
    generate_license_badge,
    generate_pypi_version_badge,
    generate_python_versions_badge,
    generate_synced_with_rhiza_badge,
    get_badge_config,
    write_badge,
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
def pyproject_file(temp_dir):
    """Create a pyproject.toml file with sample data."""
    pyproject_content = {
        "project": {
            "name": "test-package",
            "version": "1.0.0",
            "license": "MIT",
            "requires-python": ">=3.11",
            "urls": {
                "Homepage": "https://github.com/test-owner/test-repo",
            },
        }
    }
    with open(temp_dir / "pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(pyproject_content))
    return temp_dir / "pyproject.toml"


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
    """Create a .cfg.toml file with generate-badges config."""
    rhiza_dir = temp_dir / ".rhiza"
    rhiza_dir.mkdir(parents=True)
    cfg_file = rhiza_dir / ".cfg.toml"
    cfg_content = """
[tool.generate-badges]
output_dir = "_custom/badges"
badges = ["synced-with-rhiza", "coverage"]

[tool.generate-badges.coverage]
coverage_json = "_custom/coverage.json"
badge_filename = "my-coverage.json"

[tool.generate-badges.coverage.thresholds]
95 = "brightgreen"
85 = "green"
75 = "yellow"
0 = "red"
"""
    with open(cfg_file, "w") as f:
        f.write(cfg_content)
    return cfg_file


class TestGenerateSyncedWithRhizaBadge:
    """Tests for generate_synced_with_rhiza_badge function."""

    def test_generates_correct_badge(self):
        """Test that the synced-with-rhiza badge has correct structure."""
        badge = generate_synced_with_rhiza_badge()
        assert badge["schemaVersion"] == 1
        assert badge["label"] == "synced with"
        assert badge["message"] == "rhiza"
        assert badge["color"] == "2FA4A9"
        assert "logoSvg" in badge
        assert "<svg" in badge["logoSvg"]


class TestGenerateCoverageBadge:
    """Tests for generate_coverage_badge function."""

    def test_generates_correct_badge(self, coverage_json_file):
        """Test that coverage badge is generated correctly."""
        badge = generate_coverage_badge(coverage_json_file, DEFAULT_COVERAGE_THRESHOLDS)
        assert badge is not None
        assert badge["schemaVersion"] == 1
        assert badge["label"] == "coverage"
        assert badge["message"] == "86%"  # 85.5 rounded
        assert badge["color"] == "green"  # 85% is in green range

    def test_missing_file_returns_none(self, temp_dir):
        """Test that missing file returns None."""
        badge = generate_coverage_badge(temp_dir / "nonexistent.json", DEFAULT_COVERAGE_THRESHOLDS)
        assert badge is None

    def test_invalid_json_returns_none(self, temp_dir):
        """Test that invalid JSON returns None."""
        bad_file = temp_dir / "bad.json"
        with open(bad_file, "w") as f:
            f.write("not json")
        badge = generate_coverage_badge(bad_file, DEFAULT_COVERAGE_THRESHOLDS)
        assert badge is None

    def test_color_thresholds(self, temp_dir):
        """Test various coverage percentages return correct colors."""
        test_cases = [
            (95, "brightgreen"),
            (85, "green"),
            (75, "yellowgreen"),
            (65, "yellow"),
            (55, "orange"),
            (25, "red"),
        ]
        for percentage, expected_color in test_cases:
            coverage_file = temp_dir / f"coverage_{percentage}.json"
            with open(coverage_file, "w") as f:
                json.dump({"totals": {"percent_covered": percentage}}, f)
            badge = generate_coverage_badge(coverage_file, DEFAULT_COVERAGE_THRESHOLDS)
            assert badge is not None
            assert badge["color"] == expected_color, f"Failed for {percentage}%"


class TestGeneratePypiVersionBadge:
    """Tests for generate_pypi_version_badge function."""

    def test_generates_correct_badge(self):
        """Test that PyPI badge is generated correctly."""
        badge = generate_pypi_version_badge("test-package")
        assert badge is not None
        assert badge["schemaVersion"] == 1
        assert badge["label"] == "pypi"
        assert badge["message"] == "test-package"
        assert badge["color"] == "blue"

    def test_no_package_name_returns_none(self):
        """Test that None package name returns None."""
        badge = generate_pypi_version_badge(None)
        assert badge is None


class TestGenerateLicenseBadge:
    """Tests for generate_license_badge function."""

    def test_mit_license(self):
        """Test MIT license badge."""
        badge = generate_license_badge("MIT")
        assert badge is not None
        assert badge["message"] == "MIT"
        assert badge["color"] == "green"

    def test_apache_license(self):
        """Test Apache license badge."""
        badge = generate_license_badge("Apache-2.0")
        assert badge is not None
        assert badge["message"] == "Apache-2.0"
        assert badge["color"] == "blue"

    def test_unknown_license(self):
        """Test unknown license gets default color."""
        badge = generate_license_badge("Custom-License")
        assert badge is not None
        assert badge["message"] == "Custom-License"
        assert badge["color"] == "lightgrey"

    def test_no_license_returns_none(self):
        """Test that None license returns None."""
        badge = generate_license_badge(None)
        assert badge is None


class TestGeneratePythonVersionsBadge:
    """Tests for generate_python_versions_badge function."""

    def test_generates_correct_badge(self):
        """Test Python versions badge is generated correctly."""
        versions = ["3.11", "3.12", "3.13"]
        badge = generate_python_versions_badge(versions)
        assert badge is not None
        assert badge["label"] == "python"
        assert badge["message"] == "3.11 | 3.12 | 3.13"
        assert badge["color"] == "blue"

    def test_empty_versions_returns_none(self):
        """Test that empty versions list returns None."""
        badge = generate_python_versions_badge([])
        assert badge is None


class TestGenerateDownloadsBadge:
    """Tests for generate_downloads_badge function."""

    def test_generates_correct_badge(self):
        """Test downloads badge is generated correctly."""
        badge = generate_downloads_badge("test-package")
        assert badge is not None
        assert badge["label"] == "downloads"
        assert badge["color"] == "orange"

    def test_no_package_returns_none(self):
        """Test that None package returns None."""
        badge = generate_downloads_badge(None)
        assert badge is None


class TestGenerateCodefactorBadge:
    """Tests for generate_codefactor_badge function."""

    def test_generates_correct_badge(self):
        """Test CodeFactor badge is generated correctly."""
        badge = generate_codefactor_badge("test-owner", "test-repo")
        assert badge is not None
        assert badge["label"] == "codefactor"
        assert badge["message"] == "test-owner/test-repo"

    def test_missing_info_returns_none(self):
        """Test that missing GitHub info returns None."""
        assert generate_codefactor_badge(None, "repo") is None
        assert generate_codefactor_badge("owner", None) is None
        assert generate_codefactor_badge(None, None) is None


class TestWriteBadge:
    """Tests for write_badge function."""

    def test_writes_badge_file(self, temp_dir):
        """Test that badge file is written correctly."""
        badge_data = {"schemaVersion": 1, "label": "test", "message": "ok"}
        output_path = temp_dir / "test-badge.json"
        result = write_badge(badge_data, output_path)
        assert result is True
        assert output_path.exists()
        with open(output_path) as f:
            written_data = json.load(f)
        assert written_data == badge_data

    def test_creates_parent_directories(self, temp_dir):
        """Test that parent directories are created."""
        badge_data = {"schemaVersion": 1, "label": "test", "message": "ok"}
        output_path = temp_dir / "nested" / "dirs" / "badge.json"
        result = write_badge(badge_data, output_path)
        assert result is True
        assert output_path.exists()

    def test_dry_run_does_not_write(self, temp_dir):
        """Test that dry run does not write files."""
        badge_data = {"schemaVersion": 1, "label": "test", "message": "ok"}
        output_path = temp_dir / "test-badge.json"
        result = write_badge(badge_data, output_path, dry_run=True)
        assert result is True
        assert not output_path.exists()


class TestGetBadgeConfig:
    """Tests for get_badge_config function."""

    def test_defaults_without_config_file(self, temp_dir):
        """Test that defaults are used when no config file exists."""
        config = get_badge_config()
        assert config.output_dir == Path("_book/badges")
        assert BadgeType.SYNCED_WITH_RHIZA in config.badges

    def test_reads_from_config_file(self, cfg_toml_file):
        """Test that config is read from .cfg.toml file."""
        config = get_badge_config()
        assert config.output_dir == Path("_custom/badges")
        assert config.coverage_json == Path("_custom/coverage.json")
        assert config.coverage_filename == "my-coverage.json"

    def test_reads_pyproject_info(self, pyproject_file):
        """Test that package info is read from pyproject.toml."""
        config = get_badge_config()
        assert config.package_name == "test-package"
        assert config.license_type == "MIT"
        assert "3.11" in config.python_versions
        assert config.github_owner == "test-owner"
        assert config.github_repo == "test-repo"


class TestGenerateBadgesCommand:
    """Tests for generate_badges_command function."""

    def test_generates_synced_with_rhiza_by_default(self, temp_dir):
        """Test that synced-with-rhiza badge is generated by default."""
        output_dir = temp_dir / "_book" / "badges"
        generate_badges_command(output_dir=output_dir)
        assert (output_dir / "synced-with-rhiza.json").exists()

    def test_with_badges_option(self, coverage_json_file, temp_dir):
        """Test --badges option generates specified badges."""
        output_dir = temp_dir / "_book" / "badges"
        generate_badges_command(output_dir=output_dir, badges=["synced-with-rhiza", "coverage"])
        assert (output_dir / "synced-with-rhiza.json").exists()
        assert (output_dir / "coverage-badge.json").exists()

    def test_all_badges_flag(self, coverage_json_file, pyproject_file, temp_dir):
        """Test --all flag generates all badges."""
        output_dir = temp_dir / "_book" / "badges"
        generate_badges_command(output_dir=output_dir, all_badges=True)
        assert (output_dir / "synced-with-rhiza.json").exists()
        # Other badges depend on having the right data

    def test_dry_run_does_not_create_files(self, temp_dir):
        """Test that dry run does not create files."""
        output_dir = temp_dir / "_book" / "badges"
        generate_badges_command(output_dir=output_dir, dry_run=True)
        assert not output_dir.exists()


class TestGenerateBadgesCLI:
    """Tests for the CLI generate-badges command."""

    def test_cli_help(self):
        """Test that help output works."""
        result = runner.invoke(app, ["generate-badges", "--help"])
        assert result.exit_code == 0
        assert "generate-badges" in result.output
        assert "--badges" in result.output
        assert "--update-readme" in result.output
        assert "--all" in result.output

    def test_cli_default_generates_synced_badge(self, temp_dir):
        """Test CLI default generates synced-with-rhiza badge."""
        output_dir = temp_dir / "_book" / "badges"
        result = runner.invoke(
            app,
            ["generate-badges", "--output-dir", str(output_dir)],
        )
        assert result.exit_code == 0
        assert "Generated 1 badge" in result.output
        assert (output_dir / "synced-with-rhiza.json").exists()

    def test_cli_with_badges(self, coverage_json_file, temp_dir):
        """Test CLI with --badges option."""
        output_dir = temp_dir / "_book" / "badges"
        result = runner.invoke(
            app,
            [
                "generate-badges",
                "--output-dir",
                str(output_dir),
                "--badges",
                "synced-with-rhiza,coverage",
            ],
        )
        assert result.exit_code == 0
        assert (output_dir / "synced-with-rhiza.json").exists()
        assert (output_dir / "coverage-badge.json").exists()

    def test_cli_dry_run(self, temp_dir):
        """Test CLI with --dry-run flag."""
        output_dir = temp_dir / "_book" / "badges"
        result = runner.invoke(
            app,
            ["generate-badges", "--output-dir", str(output_dir), "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Would generate" in result.output
        assert not output_dir.exists()

    def test_cli_all_badges(self, coverage_json_file, pyproject_file, temp_dir):
        """Test CLI with --all flag."""
        output_dir = temp_dir / "_book" / "badges"
        result = runner.invoke(
            app,
            ["generate-badges", "--output-dir", str(output_dir), "--all"],
        )
        assert result.exit_code == 0
        assert (output_dir / "synced-with-rhiza.json").exists()


class TestUpdateReadme:
    """Tests for adding badges to README."""

    def test_adds_badge_to_empty_readme(self, temp_dir):
        """Test adding badge to README with just a heading."""
        readme = temp_dir / "README.md"
        readme.write_text("# My Project\n\nSome description.\n")

        result = runner.invoke(
            app,
            [
                "generate-badges",
                "--output-dir",
                str(temp_dir / "badges"),
                "--update-readme",
                "--readme",
                str(readme),
                "--badge-url-base",
                "https://example.com/badges",
            ],
        )
        assert result.exit_code == 0

        content = readme.read_text()
        assert "synced" in content.lower() or "rhiza" in content.lower()
        assert "shields.io" in content

    def test_does_not_duplicate_existing_badge(self, temp_dir):
        """Test that existing badges are not duplicated."""
        readme = temp_dir / "README.md"
        original_content = """# My Project
![Synced with Rhiza](https://img.shields.io/badge/synced%20with-rhiza-2FA4A9)

Some description.
"""
        readme.write_text(original_content)

        result = runner.invoke(
            app,
            [
                "generate-badges",
                "--output-dir",
                str(temp_dir / "badges"),
                "--update-readme",
                "--readme",
                str(readme),
                "--badge-url-base",
                "https://example.com/badges",
            ],
        )
        assert result.exit_code == 0

        content = readme.read_text()
        # Should not add duplicate
        assert content.count("synced") == 1

    def test_dry_run_does_not_modify_readme(self, temp_dir):
        """Test that dry-run does not modify README."""
        readme = temp_dir / "README.md"
        original_content = "# My Project\n\nSome description.\n"
        readme.write_text(original_content)

        result = runner.invoke(
            app,
            [
                "generate-badges",
                "--output-dir",
                str(temp_dir / "badges"),
                "--update-readme",
                "--readme",
                str(readme),
                "--badge-url-base",
                "https://example.com/badges",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Would add" in result.output

        # README should be unchanged
        assert readme.read_text() == original_content

    def test_warns_without_badge_url_base(self, temp_dir):
        """Test that warning is shown when badge-url-base is not specified."""
        readme = temp_dir / "README.md"
        readme.write_text("# My Project\n")

        result = runner.invoke(
            app,
            [
                "generate-badges",
                "--output-dir",
                str(temp_dir / "badges"),
                "--update-readme",
                "--readme",
                str(readme),
            ],
        )
        assert result.exit_code == 0
        assert "Warning" in result.output or "warning" in result.output.lower()

    def test_inserts_after_existing_badges(self, temp_dir):
        """Test that new badges are inserted after existing badges."""
        readme = temp_dir / "README.md"
        readme.write_text("""# My Project
[![CI](https://img.shields.io/badge/CI-passing-green)](https://example.com)

Some description.
""")

        result = runner.invoke(
            app,
            [
                "generate-badges",
                "--output-dir",
                str(temp_dir / "badges"),
                "--update-readme",
                "--readme",
                str(readme),
                "--badge-url-base",
                "https://example.com/badges",
            ],
        )
        assert result.exit_code == 0

        content = readme.read_text()
        # New badge should be after the CI badge
        ci_pos = content.find("CI-passing")
        rhiza_pos = content.find("rhiza")
        assert rhiza_pos > ci_pos

    def test_ignores_badges_in_code_blocks(self, temp_dir: Path) -> None:
        """Test that badges in code blocks are not detected as existing."""
        readme = temp_dir / "README.md"
        # Synced with Rhiza badge is inside a markdown code block - should be ignored
        readme.write_text("""# Test Project

Here's an example of using badges:

```markdown
![Synced with Rhiza](https://img.shields.io/endpoint?url=https://example.com/synced-with-rhiza.json)
```

This should not prevent adding the actual badge.
""")

        result = runner.invoke(
            app,
            [
                "generate-badges",
                "--output-dir",
                str(temp_dir / "badges"),
                "--update-readme",
                "--readme",
                str(readme),
                "--badge-url-base",
                "https://example.com/badges",
            ],
        )
        assert result.exit_code == 0

        content = readme.read_text()
        # Should have added the synced-with-rhiza badge (not skipped due to code block)
        # Count badge image syntax - there should be 2: one in code block, one added
        # The alt text "Synced with Rhiza" appears in both
        assert content.count("![Synced with Rhiza]") == 2

    def test_updates_changed_badge(self, temp_dir: Path) -> None:
        """Test that badges are updated when they have changed."""
        readme = temp_dir / "README.md"
        # Old-style coverage badge with endpoint
        readme.write_text("""# My Project
[![Coverage](https://img.shields.io/endpoint?url=https://old-url.com/badges/coverage-badge.json)](https://old-url.com/coverage)

Some description.
""")
        # Create coverage.json file
        coverage_json = temp_dir / "_tests" / "coverage.json"
        coverage_json.parent.mkdir(parents=True, exist_ok=True)
        coverage_json.write_text('{"totals": {"percent_covered": 85.0}}')

        result = runner.invoke(
            app,
            [
                "generate-badges",
                "--output-dir",
                str(temp_dir / "badges"),
                "--badges",
                "coverage",
                "--update-readme",
                "--readme",
                str(readme),
                "--badge-url-base",
                "https://new-url.com/badges",
            ],
        )
        assert result.exit_code == 0

        content = readme.read_text()
        # Old badge should be replaced with new one
        assert "old-url.com" not in content
        assert "new-url.com" in content
        # Should still only have one coverage badge
        assert content.count("Coverage") == 1
