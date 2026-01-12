"""Comprehensive unit tests for coverage badge generation command."""

import json

import pytest

from rhiza_tools.commands.generate_badge import (
    generate_coverage_badge_command,
    get_badge_color,
)


class TestGetBadgeColor:
    """Tests for the get_badge_color function."""

    def test_brightgreen_for_90_and_above(self):
        """Test that coverage >= 90% returns brightgreen."""
        assert get_badge_color(90) == "brightgreen"
        assert get_badge_color(95) == "brightgreen"
        assert get_badge_color(100) == "brightgreen"

    def test_green_for_80_to_89(self):
        """Test that coverage 80-89% returns green."""
        assert get_badge_color(80) == "green"
        assert get_badge_color(85) == "green"
        assert get_badge_color(89) == "green"

    def test_yellowgreen_for_70_to_79(self):
        """Test that coverage 70-79% returns yellowgreen."""
        assert get_badge_color(70) == "yellowgreen"
        assert get_badge_color(75) == "yellowgreen"
        assert get_badge_color(79) == "yellowgreen"

    def test_yellow_for_60_to_69(self):
        """Test that coverage 60-69% returns yellow."""
        assert get_badge_color(60) == "yellow"
        assert get_badge_color(65) == "yellow"
        assert get_badge_color(69) == "yellow"

    def test_orange_for_50_to_59(self):
        """Test that coverage 50-59% returns orange."""
        assert get_badge_color(50) == "orange"
        assert get_badge_color(55) == "orange"
        assert get_badge_color(59) == "orange"

    def test_red_for_below_50(self):
        """Test that coverage < 50% returns red."""
        assert get_badge_color(0) == "red"
        assert get_badge_color(25) == "red"
        assert get_badge_color(49) == "red"

    def test_boundary_values(self):
        """Test exact boundary values for color thresholds."""
        # Test boundaries between color ranges
        assert get_badge_color(89) == "green"
        assert get_badge_color(90) == "brightgreen"

        assert get_badge_color(79) == "yellowgreen"
        assert get_badge_color(80) == "green"

        assert get_badge_color(69) == "yellow"
        assert get_badge_color(70) == "yellowgreen"

        assert get_badge_color(59) == "orange"
        assert get_badge_color(60) == "yellow"

        assert get_badge_color(49) == "red"
        assert get_badge_color(50) == "orange"


class TestGenerateCoverageBadgeCommand:
    """Tests for the generate_coverage_badge_command function."""

    def test_successful_badge_generation(self, tmp_path, capsys):
        """Test successful generation of coverage badge with valid data."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "output" / "badge.json"

        coverage_data = {
            "totals": {
                "percent_covered": 85.7,
            }
        }
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Execute
        generate_coverage_badge_command(coverage_json_path, output_path)

        # Verify output file was created
        assert output_path.exists()

        # Verify content
        badge_data = json.loads(output_path.read_text())
        assert badge_data["schemaVersion"] == 1
        assert badge_data["label"] == "coverage"
        assert badge_data["message"] == "86%"  # Rounded from 85.7
        assert badge_data["color"] == "green"

        # Verify console output
        captured = capsys.readouterr()
        assert "[INFO] Generating coverage badge" in captured.out
        assert "[INFO] Coverage: 86%" in captured.out
        assert "[INFO] Coverage badge JSON generated" in captured.out

    def test_missing_coverage_json_file(self, tmp_path, capsys):
        """Test that missing coverage.json file prints warning and returns without error."""
        # Setup
        coverage_json_path = tmp_path / "nonexistent.json"
        output_path = tmp_path / "badge.json"

        # Execute - should not raise an exception
        generate_coverage_badge_command(coverage_json_path, output_path)

        # Verify warning was printed
        captured = capsys.readouterr()
        assert "[WARN] Coverage JSON file not found" in captured.err
        assert "skipping badge generation" in captured.err

        # Verify no output file was created
        assert not output_path.exists()

    def test_invalid_json_format(self, tmp_path, capsys):
        """Test that invalid JSON format causes SystemExit."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "badge.json"

        # Write invalid JSON
        coverage_json_path.write_text("{ invalid json }")

        # Execute and verify it exits with error
        with pytest.raises(SystemExit) as excinfo:
            generate_coverage_badge_command(coverage_json_path, output_path)

        assert excinfo.value.code == 1

        # Verify error message
        captured = capsys.readouterr()
        assert "[ERROR] Failed to parse coverage JSON" in captured.err

    def test_missing_totals_key(self, tmp_path, capsys):
        """Test that missing 'totals' key causes SystemExit."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "badge.json"

        coverage_data = {"some_other_key": "value"}
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Execute and verify it exits with error
        with pytest.raises(SystemExit) as excinfo:
            generate_coverage_badge_command(coverage_json_path, output_path)

        assert excinfo.value.code == 1

        # Verify error message
        captured = capsys.readouterr()
        assert "[ERROR] Missing expected key in coverage JSON" in captured.err
        assert "totals" in captured.err

    def test_missing_percent_covered_key(self, tmp_path, capsys):
        """Test that missing 'percent_covered' key causes SystemExit."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "badge.json"

        coverage_data = {"totals": {"some_other_key": "value"}}
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Execute and verify it exits with error
        with pytest.raises(SystemExit) as excinfo:
            generate_coverage_badge_command(coverage_json_path, output_path)

        assert excinfo.value.code == 1

        # Verify error message
        captured = capsys.readouterr()
        assert "[ERROR] Missing expected key in coverage JSON" in captured.err
        assert "percent_covered" in captured.err

    def test_coverage_value_below_zero(self, tmp_path, capsys):
        """Test that coverage value < 0 causes SystemExit."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "badge.json"

        coverage_data = {"totals": {"percent_covered": -5.0}}
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Execute and verify it exits with error
        with pytest.raises(SystemExit) as excinfo:
            generate_coverage_badge_command(coverage_json_path, output_path)

        assert excinfo.value.code == 1

        # Verify error message
        captured = capsys.readouterr()
        assert "[ERROR] Coverage percentage -5 is out of valid range 0-100" in captured.err

    def test_coverage_value_above_100(self, tmp_path, capsys):
        """Test that coverage value > 100 causes SystemExit."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "badge.json"

        coverage_data = {"totals": {"percent_covered": 150.0}}
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Execute and verify it exits with error
        with pytest.raises(SystemExit) as excinfo:
            generate_coverage_badge_command(coverage_json_path, output_path)

        assert excinfo.value.code == 1

        # Verify error message
        captured = capsys.readouterr()
        assert "[ERROR] Coverage percentage 150 is out of valid range 0-100" in captured.err

    def test_output_directory_creation(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "nested" / "dir" / "badge.json"

        coverage_data = {"totals": {"percent_covered": 75.0}}
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Verify directory doesn't exist yet
        assert not output_path.parent.exists()

        # Execute
        generate_coverage_badge_command(coverage_json_path, output_path)

        # Verify directory was created
        assert output_path.parent.exists()
        assert output_path.exists()

    def test_rounding_behavior(self, tmp_path):
        """Test that coverage percentages are rounded correctly."""
        test_cases = [
            (85.4, "85%"),  # Rounds down
            (85.5, "86%"),  # Rounds up
            (85.6, "86%"),  # Rounds up
            (90.0, "90%"),  # Exact value
            (99.9, "100%"),  # Rounds up to 100
            (0.1, "0%"),  # Rounds down to 0
        ]

        for percent, expected_message in test_cases:
            # Setup
            coverage_json_path = tmp_path / "coverage.json"
            output_path = tmp_path / f"badge_{percent}.json"

            coverage_data = {"totals": {"percent_covered": percent}}
            coverage_json_path.write_text(json.dumps(coverage_data))

            # Execute
            generate_coverage_badge_command(coverage_json_path, output_path)

            # Verify
            badge_data = json.loads(output_path.read_text())
            assert badge_data["message"] == expected_message, (
                f"Expected {expected_message} for {percent}%, got {badge_data['message']}"
            )

    def test_badge_json_format(self, tmp_path):
        """Test that generated badge JSON has correct format and structure."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "badge.json"

        coverage_data = {"totals": {"percent_covered": 92.5}}
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Execute
        generate_coverage_badge_command(coverage_json_path, output_path)

        # Verify JSON structure
        badge_data = json.loads(output_path.read_text())

        # Check all required fields exist
        assert "schemaVersion" in badge_data
        assert "label" in badge_data
        assert "message" in badge_data
        assert "color" in badge_data

        # Check field types
        assert isinstance(badge_data["schemaVersion"], int)
        assert isinstance(badge_data["label"], str)
        assert isinstance(badge_data["message"], str)
        assert isinstance(badge_data["color"], str)

        # Check values
        assert badge_data["schemaVersion"] == 1
        assert badge_data["label"] == "coverage"
        assert badge_data["message"].endswith("%")

        # Verify file has trailing newline
        content = output_path.read_text()
        assert content.endswith("\n")

    def test_all_coverage_thresholds(self, tmp_path):
        """Test badge generation across all color threshold boundaries."""
        test_cases = [
            (95.0, "brightgreen"),
            (90.0, "brightgreen"),
            (85.0, "green"),
            (80.0, "green"),
            (75.0, "yellowgreen"),
            (70.0, "yellowgreen"),
            (65.0, "yellow"),
            (60.0, "yellow"),
            (55.0, "orange"),
            (50.0, "orange"),
            (45.0, "red"),
            (0.0, "red"),
        ]

        for percent, expected_color in test_cases:
            # Setup
            coverage_json_path = tmp_path / "coverage.json"
            output_path = tmp_path / f"badge_{percent}.json"

            coverage_data = {"totals": {"percent_covered": percent}}
            coverage_json_path.write_text(json.dumps(coverage_data))

            # Execute
            generate_coverage_badge_command(coverage_json_path, output_path)

            # Verify
            badge_data = json.loads(output_path.read_text())
            assert badge_data["color"] == expected_color, (
                f"Expected {expected_color} for {percent}%, got {badge_data['color']}"
            )

    def test_overwrites_existing_badge(self, tmp_path):
        """Test that existing badge file is overwritten with new data."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "badge.json"

        # Create existing badge with different data
        existing_badge = {
            "schemaVersion": 1,
            "label": "coverage",
            "message": "50%",
            "color": "orange",
        }
        output_path.write_text(json.dumps(existing_badge))

        # Create new coverage data
        coverage_data = {"totals": {"percent_covered": 95.0}}
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Execute
        generate_coverage_badge_command(coverage_json_path, output_path)

        # Verify file was overwritten
        badge_data = json.loads(output_path.read_text())
        assert badge_data["message"] == "95%"
        assert badge_data["color"] == "brightgreen"

    def test_edge_case_zero_coverage(self, tmp_path):
        """Test handling of 0% coverage."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "badge.json"

        coverage_data = {"totals": {"percent_covered": 0.0}}
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Execute
        generate_coverage_badge_command(coverage_json_path, output_path)

        # Verify
        badge_data = json.loads(output_path.read_text())
        assert badge_data["message"] == "0%"
        assert badge_data["color"] == "red"

    def test_edge_case_100_coverage(self, tmp_path):
        """Test handling of 100% coverage."""
        # Setup
        coverage_json_path = tmp_path / "coverage.json"
        output_path = tmp_path / "badge.json"

        coverage_data = {"totals": {"percent_covered": 100.0}}
        coverage_json_path.write_text(json.dumps(coverage_data))

        # Execute
        generate_coverage_badge_command(coverage_json_path, output_path)

        # Verify
        badge_data = json.loads(output_path.read_text())
        assert badge_data["message"] == "100%"
        assert badge_data["color"] == "brightgreen"
