"""Command to generate a coverage badge endpoint JSON for shields.io."""

import json
from dataclasses import dataclass
from pathlib import Path

import typer
from loguru import logger

# Default configuration values
DEFAULT_COVERAGE_JSON = "_tests/coverage.json"
DEFAULT_OUTPUT_DIR = "_book/tests"
DEFAULT_BADGE_FILENAME = "coverage-badge.json"

# Color thresholds (percentage -> color)
DEFAULT_THRESHOLDS = {
    90: "brightgreen",
    80: "green",
    70: "yellowgreen",
    60: "yellow",
    50: "orange",
    0: "red",
}


@dataclass
class CoverageBadgeConfig:
    """Configuration for coverage badge generation."""

    coverage_json: Path
    output_dir: Path
    badge_filename: str
    thresholds: dict[int, str]

    @property
    def badge_path(self) -> Path:
        """Get the full path to the badge JSON file."""
        return self.output_dir / self.badge_filename


def get_coverage_badge_config(
    coverage_json: Path | None = None,
    output_dir: Path | None = None,
    badge_filename: str | None = None,
) -> CoverageBadgeConfig:
    """Get coverage badge configuration from .cfg.toml or defaults.

    Args:
        coverage_json: Override path to coverage.json file.
        output_dir: Override path to output directory.
        badge_filename: Override badge filename.

    Returns:
        CoverageBadgeConfig with settings from config file or defaults.
    """
    from rhiza_tools.config import load_config

    config = load_config()
    cfg = config.coverage_badge

    # Use provided values, then config file, then defaults
    resolved_coverage_json = coverage_json or Path(
        cfg.get("coverage_json", DEFAULT_COVERAGE_JSON)
    )
    resolved_output_dir = output_dir or Path(
        cfg.get("output_dir", DEFAULT_OUTPUT_DIR)
    )
    resolved_badge_filename = badge_filename or cfg.get(
        "badge_filename", DEFAULT_BADGE_FILENAME
    )

    # Load thresholds from config or use defaults
    config_thresholds = cfg.get("thresholds", {})
    if config_thresholds:
        # Convert string keys to int
        thresholds = {int(k): v for k, v in config_thresholds.items()}
    else:
        thresholds = DEFAULT_THRESHOLDS.copy()

    return CoverageBadgeConfig(
        coverage_json=resolved_coverage_json,
        output_dir=resolved_output_dir,
        badge_filename=resolved_badge_filename,
        thresholds=thresholds,
    )


def extract_coverage_percentage(coverage_json_path: Path) -> float:
    """Extract coverage percentage from coverage.json file.

    Args:
        coverage_json_path: Path to the coverage.json file.

    Returns:
        Coverage percentage as a float.

    Raises:
        typer.Exit: If the file cannot be read or parsed.
    """
    try:
        with open(coverage_json_path) as f:
            data = json.load(f)
        return data["totals"]["percent_covered"]
    except FileNotFoundError:
        logger.warning(f"Coverage JSON file not found at {coverage_json_path}")
        raise typer.Exit(code=0)
    except KeyError as e:
        logger.error(f"Missing key in coverage JSON: {e}")
        raise typer.Exit(code=1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in coverage file: {e}")
        raise typer.Exit(code=1)


def get_badge_color(percentage: float, thresholds: dict[int, str]) -> str:
    """Determine badge color based on coverage percentage.

    Args:
        percentage: Coverage percentage.
        thresholds: Dictionary mapping minimum percentages to colors.

    Returns:
        Color string for shields.io badge.
    """
    # Sort thresholds in descending order
    for threshold in sorted(thresholds.keys(), reverse=True):
        if percentage >= threshold:
            return thresholds[threshold]
    # Fallback to red if no threshold matches
    return "red"


def generate_badge_json(percentage: float, color: str) -> dict:
    """Generate shields.io endpoint JSON.

    Args:
        percentage: Coverage percentage.
        color: Color string for the badge.

    Returns:
        Dictionary suitable for shields.io endpoint.
    """
    return {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{percentage:.0f}%",
        "color": color,
    }


def coverage_badge_command(
    coverage_json: Path | None = None,
    output_dir: Path | None = None,
    badge_filename: str | None = None,
    dry_run: bool = False,
) -> None:
    """Generate a coverage badge endpoint JSON for shields.io.

    Args:
        coverage_json: Path to coverage.json file. Defaults to config or _tests/coverage.json.
        output_dir: Path to output directory. Defaults to config or _book/tests.
        badge_filename: Badge filename. Defaults to config or coverage-badge.json.
        dry_run: If True, print what would happen without writing files.
    """
    config = get_coverage_badge_config(coverage_json, output_dir, badge_filename)

    logger.info(f"Generating coverage badge from {config.coverage_json}...")

    # Extract coverage percentage
    percentage = extract_coverage_percentage(config.coverage_json)
    rounded_percentage = round(percentage)

    logger.info(f"Coverage: {rounded_percentage}%")

    # Determine badge color
    color = get_badge_color(rounded_percentage, config.thresholds)

    # Generate badge JSON
    badge_data = generate_badge_json(rounded_percentage, color)

    if dry_run:
        typer.echo(f"Would write badge JSON to {config.badge_path}:")
        typer.echo(json.dumps(badge_data, indent=2))
        return

    # Create output directory if it doesn't exist
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Write badge JSON
    with open(config.badge_path, "w") as f:
        json.dump(badge_data, f, indent=2)
        f.write("\n")  # Add trailing newline

    logger.info(f"Coverage badge JSON generated at {config.badge_path}")
    typer.echo(f"✓ Coverage badge generated: {config.badge_path}")
