#!/usr/bin/env python3
"""Generate a coverage badge endpoint JSON for shields.io.

This script reads a coverage report JSON file and creates a shields.io endpoint
JSON file for a coverage badge at a specified output path.
"""

import json
from pathlib import Path

import typer

from rhiza_tools import console

# Coverage percentage bounds and the (minimum coverage, shields.io color) ladder,
# ordered from highest to lowest. Higher coverage gets "greener" colors.
MIN_COVERAGE = 0
MAX_COVERAGE = 100
_COLOR_THRESHOLDS: list[tuple[int, str]] = [
    (90, "brightgreen"),
    (80, "green"),
    (70, "yellowgreen"),
    (60, "yellow"),
    (50, "orange"),
]
_DEFAULT_COLOR = "red"


def get_badge_color(coverage: int) -> str:
    """Determine badge color based on coverage percentage.

    Colors follow a common convention where higher coverage gets "greener" colors.

    Args:
        coverage: Coverage percentage (0-100).

    Returns:
        Color name for shields.io badge.

    Example:
        >>> color = get_badge_color(95)
        >>> print(color)
        brightgreen

        >>> color = get_badge_color(45)
        >>> print(color)
        red
    """
    for threshold, color in _COLOR_THRESHOLDS:
        if coverage >= threshold:
            return color
    return _DEFAULT_COLOR


def generate_coverage_badge_command(
    coverage_json_path: Path,
    output_path: Path,
) -> None:
    """Generate coverage badge JSON from coverage report.

    Reads a pytest-cov generated coverage.json file and creates a shields.io
    endpoint JSON file with appropriate color coding based on coverage percentage.

    Args:
        coverage_json_path: Path to the coverage.json file.
        output_path: Path where the badge JSON should be written.

    Raises:
        typer.Exit: If the coverage JSON is invalid or missing required data.

    Example:
        Generate badge from coverage report::

            from pathlib import Path
            generate_coverage_badge_command(
                Path("_tests/coverage.json"),
                Path("_book/tests/coverage-badge.json")
            )

        The generated JSON can be used with shields.io::

            https://img.shields.io/endpoint?url=<url-to-badge-json>
    """
    # Check if coverage.json exists
    if not coverage_json_path.exists():
        console.warning(
            f"Coverage JSON file not found at {coverage_json_path}, skipping badge generation",
        )
        return

    console.info(f"Generating coverage badge from {coverage_json_path}...")

    # Read and parse coverage data
    try:
        with coverage_json_path.open("r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        console.error(f"Failed to parse coverage JSON: {e}")
        raise typer.Exit(code=1) from e

    # Extract coverage percentage
    try:
        percent = data["totals"]["percent_covered"]
    except KeyError as e:
        console.error(f"Missing expected key in coverage JSON: {e}")
        raise typer.Exit(code=1) from e

    # Round to nearest integer
    coverage = round(percent)

    if not MIN_COVERAGE <= coverage <= MAX_COVERAGE:
        console.error(f"Coverage percentage {coverage} is out of valid range 0-100")
        raise typer.Exit(code=1)

    console.info(f"Coverage: {coverage}%")

    # Determine badge color
    color = get_badge_color(coverage)

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate shields.io endpoint JSON
    badge_data = {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{coverage}%",
        "color": color,
    }

    with output_path.open("w") as f:
        json.dump(badge_data, f, indent=2)
        f.write("\n")  # Add trailing newline

    console.info(f"Coverage badge JSON generated at {output_path}")
