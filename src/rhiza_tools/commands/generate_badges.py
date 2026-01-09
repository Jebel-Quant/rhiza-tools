"""Command to generate various badges for shields.io."""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import tomlkit
import typer
from loguru import logger


# Badge type enumeration
class BadgeType(str, Enum):
    """Supported badge types."""

    SYNCED_WITH_RHIZA = "synced-with-rhiza"
    COVERAGE = "coverage"
    PYPI_VERSION = "pypi-version"
    LICENSE = "license"
    PYTHON_VERSIONS = "python-versions"
    DOWNLOADS = "downloads"
    CODEFACTOR = "codefactor"


# Default configuration values
DEFAULT_OUTPUT_DIR = "_book/badges"
DEFAULT_COVERAGE_JSON = "_tests/coverage.json"
DEFAULT_COVERAGE_FILENAME = "coverage-badge.json"

# Default color thresholds for coverage
DEFAULT_COVERAGE_THRESHOLDS = {
    90: "brightgreen",
    80: "green",
    70: "yellowgreen",
    60: "yellow",
    50: "orange",
    0: "red",
}

# License colors
LICENSE_COLORS = {
    "MIT": "green",
    "Apache-2.0": "blue",
    "GPL-3.0": "blue",
    "BSD-3-Clause": "orange",
    "BSD-2-Clause": "orange",
    "LGPL-3.0": "blue",
    "MPL-2.0": "blue",
    "ISC": "green",
    "Unlicense": "lightgrey",
}


@dataclass
class BadgeConfig:
    """Configuration for badge generation."""

    output_dir: Path
    badges: list[BadgeType]
    # Coverage-specific config
    coverage_json: Path
    coverage_filename: str
    coverage_thresholds: dict[int, str]
    # Package info (read from pyproject.toml)
    package_name: str | None = None
    license_type: str | None = None
    python_versions: list[str] = field(default_factory=list)
    github_owner: str | None = None
    github_repo: str | None = None


def get_badge_config(
    output_dir: Path | None = None,
    badges: list[BadgeType] | None = None,
) -> BadgeConfig:
    """Get badge configuration from .cfg.toml, pyproject.toml, or defaults.

    Args:
        output_dir: Override path to output directory.
        badges: Override list of badges to generate.

    Returns:
        BadgeConfig with settings from config files or defaults.
    """
    from rhiza_tools.config import load_config

    config = load_config()
    cfg = config.generate_badges

    # Resolve output directory
    resolved_output_dir = output_dir or Path(
        cfg.get("output_dir", DEFAULT_OUTPUT_DIR)
    )

    # Resolve badge list
    if badges is not None:
        resolved_badges = badges
    else:
        badge_names = cfg.get("badges", [BadgeType.SYNCED_WITH_RHIZA.value])
        resolved_badges = [BadgeType(name) for name in badge_names]

    # Coverage config
    coverage_cfg = cfg.get("coverage", {})
    coverage_json = Path(coverage_cfg.get("coverage_json", DEFAULT_COVERAGE_JSON))
    coverage_filename = coverage_cfg.get("badge_filename", DEFAULT_COVERAGE_FILENAME)

    # Coverage thresholds
    config_thresholds = coverage_cfg.get("thresholds", {})
    if config_thresholds:
        coverage_thresholds = {int(k): v for k, v in config_thresholds.items()}
    else:
        coverage_thresholds = DEFAULT_COVERAGE_THRESHOLDS.copy()

    # Read package info from pyproject.toml
    package_name = None
    license_type = None
    python_versions = []
    github_owner = None
    github_repo = None

    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        try:
            with open(pyproject_path) as f:
                pyproject = tomlkit.parse(f.read())

            project = pyproject.get("project", {})
            package_name = project.get("name")
            license_info = project.get("license")
            if isinstance(license_info, dict):
                license_type = license_info.get("text") or license_info.get("file")
            elif isinstance(license_info, str):
                license_type = license_info

            # Extract Python versions from requires-python
            requires_python = project.get("requires-python", "")
            if requires_python:
                python_versions = _parse_python_versions(requires_python)

            # Try to get GitHub info from project URLs
            urls = project.get("urls", {})
            homepage = urls.get("Homepage", "") or urls.get("Repository", "")
            if "github.com" in homepage:
                parts = homepage.rstrip("/").split("/")
                if len(parts) >= 2:
                    github_repo = parts[-1]
                    github_owner = parts[-2]

        except Exception as e:
            logger.debug(f"Could not read pyproject.toml: {e}")

    return BadgeConfig(
        output_dir=resolved_output_dir,
        badges=resolved_badges,
        coverage_json=coverage_json,
        coverage_filename=coverage_filename,
        coverage_thresholds=coverage_thresholds,
        package_name=package_name,
        license_type=license_type,
        python_versions=python_versions,
        github_owner=github_owner,
        github_repo=github_repo,
    )


def _parse_python_versions(requires_python: str) -> list[str]:
    """Parse requires-python string to list of supported versions.

    Args:
        requires_python: Version specifier like ">=3.11" or ">=3.11,<3.14"

    Returns:
        List of version strings like ["3.11", "3.12", "3.13"]
    """
    # Known Python versions
    all_versions = ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]

    # Simple parsing - handle >=X.Y
    min_version = None
    max_version = None

    for part in requires_python.replace(" ", "").split(","):
        if part.startswith(">="):
            min_version = part[2:]
        elif part.startswith(">"):
            min_version = part[1:]
        elif part.startswith("<="):
            max_version = part[2:]
        elif part.startswith("<"):
            max_version = part[1:]

    result = []
    for v in all_versions:
        if min_version and v < min_version:
            continue
        if max_version and v >= max_version:
            continue
        result.append(v)

    return result if result else all_versions[-3:]  # Default to last 3


def generate_synced_with_rhiza_badge() -> dict[str, Any]:
    """Generate the 'synced with rhiza' badge JSON.

    Returns:
        Dictionary suitable for shields.io endpoint.
    """
    return {
        "schemaVersion": 1,
        "label": "synced with",
        "message": "rhiza",
        "color": "2FA4A9",
        "logoSvg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path fill="#fff" d="M50 5C25.1 5 5 25.1 5 50s20.1 45 45 45 45-20.1 45-45S74.9 5 50 5zm0 80c-19.3 0-35-15.7-35-35s15.7-35 35-35 35 15.7 35 35-15.7 35-35 35z"/><path fill="#fff" d="M50 25c-13.8 0-25 11.2-25 25s11.2 25 25 25 25-11.2 25-25-11.2-25-25-25zm0 40c-8.3 0-15-6.7-15-15s6.7-15 15-15 15 6.7 15 15-6.7 15-15 15z"/><circle fill="#fff" cx="50" cy="50" r="8"/></svg>',
    }


def generate_coverage_badge(
    coverage_json_path: Path,
    thresholds: dict[int, str],
) -> dict[str, Any] | None:
    """Generate coverage badge JSON.

    Args:
        coverage_json_path: Path to coverage.json file.
        thresholds: Dictionary mapping minimum percentages to colors.

    Returns:
        Dictionary suitable for shields.io endpoint, or None if file not found.
    """
    try:
        with open(coverage_json_path) as f:
            data = json.load(f)
        percentage = round(data["totals"]["percent_covered"])
    except FileNotFoundError:
        logger.warning(f"Coverage JSON file not found at {coverage_json_path}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Error reading coverage JSON: {e}")
        return None

    # Determine color
    color = "red"
    for threshold in sorted(thresholds.keys(), reverse=True):
        if percentage >= threshold:
            color = thresholds[threshold]
            break

    return {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{percentage}%",
        "color": color,
    }


def generate_pypi_version_badge(package_name: str | None) -> dict[str, Any] | None:
    """Generate PyPI version badge JSON.

    Note: This creates a static badge. For dynamic badges, use shields.io directly.

    Args:
        package_name: The PyPI package name.

    Returns:
        Dictionary suitable for shields.io endpoint, or None if no package name.
    """
    if not package_name:
        logger.warning("No package name found in pyproject.toml for PyPI badge")
        return None

    return {
        "schemaVersion": 1,
        "label": "pypi",
        "message": package_name,
        "color": "blue",
        "namedLogo": "pypi",
    }


def generate_license_badge(license_type: str | None) -> dict[str, Any] | None:
    """Generate license badge JSON.

    Args:
        license_type: The license type (e.g., "MIT", "Apache-2.0").

    Returns:
        Dictionary suitable for shields.io endpoint, or None if no license.
    """
    if not license_type:
        logger.warning("No license found in pyproject.toml")
        return None

    # Clean up license type
    license_clean = license_type.strip()
    color = LICENSE_COLORS.get(license_clean, "lightgrey")

    return {
        "schemaVersion": 1,
        "label": "license",
        "message": license_clean,
        "color": color,
    }


def generate_python_versions_badge(versions: list[str]) -> dict[str, Any] | None:
    """Generate Python versions badge JSON.

    Args:
        versions: List of supported Python versions.

    Returns:
        Dictionary suitable for shields.io endpoint, or None if no versions.
    """
    if not versions:
        logger.warning("No Python versions found")
        return None

    message = " | ".join(versions)

    return {
        "schemaVersion": 1,
        "label": "python",
        "message": message,
        "color": "blue",
        "namedLogo": "python",
        "logoColor": "white",
    }


def generate_downloads_badge(package_name: str | None) -> dict[str, Any] | None:
    """Generate downloads badge JSON placeholder.

    Note: For accurate download counts, use pepy.tech or shields.io dynamic badges.

    Args:
        package_name: The PyPI package name.

    Returns:
        Dictionary suitable for shields.io endpoint, or None if no package name.
    """
    if not package_name:
        logger.warning("No package name found for downloads badge")
        return None

    return {
        "schemaVersion": 1,
        "label": "downloads",
        "message": "see PyPI",
        "color": "orange",
    }


def generate_codefactor_badge(
    github_owner: str | None,
    github_repo: str | None,
) -> dict[str, Any] | None:
    """Generate CodeFactor badge JSON placeholder.

    Note: For accurate grades, use CodeFactor's actual badge URL.

    Args:
        github_owner: GitHub repository owner.
        github_repo: GitHub repository name.

    Returns:
        Dictionary suitable for shields.io endpoint, or None if no GitHub info.
    """
    if not github_owner or not github_repo:
        logger.warning("No GitHub info found for CodeFactor badge")
        return None

    return {
        "schemaVersion": 1,
        "label": "codefactor",
        "message": f"{github_owner}/{github_repo}",
        "color": "brightgreen",
    }


def write_badge(
    badge_data: dict[str, Any],
    output_path: Path,
    dry_run: bool = False,
) -> bool:
    """Write badge JSON to file.

    Args:
        badge_data: The badge JSON data.
        output_path: Path to write the badge file.
        dry_run: If True, print instead of writing.

    Returns:
        True if successful, False otherwise.
    """
    if dry_run:
        typer.echo(f"Would write badge to {output_path}:")
        typer.echo(json.dumps(badge_data, indent=2))
        return True

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(badge_data, f, indent=2)
            f.write("\n")
        return True
    except Exception as e:
        logger.error(f"Failed to write badge to {output_path}: {e}")
        return False


# Badge markdown templates for README
# Most badges use direct shields.io/pepy.tech/codefactor URLs for reliability.
# Only coverage uses endpoint badges since it requires custom JSON data.
BADGE_MARKDOWN_TEMPLATES = {
    # Static badge - doesn't need endpoint
    BadgeType.SYNCED_WITH_RHIZA: '![Synced with Rhiza](https://img.shields.io/badge/synced%20with-rhiza-2FA4A9)',
    # Endpoint badge - needs hosted JSON for dynamic coverage %
    BadgeType.COVERAGE: '[![Coverage](https://img.shields.io/endpoint?url={badge_url})]({link_url})',
    # Direct shields.io PyPI badge
    BadgeType.PYPI_VERSION: '[![PyPI version](https://img.shields.io/pypi/v/{package_name}.svg)](https://pypi.org/project/{package_name}/)',
    # Static badge with license type
    BadgeType.LICENSE: '[![License: {license_type}](https://img.shields.io/badge/License-{license_type}-yellow.svg)](https://opensource.org/licenses/{license_type})',
    # Direct shields.io Python version badge
    BadgeType.PYTHON_VERSIONS: '![Python versions](https://img.shields.io/pypi/pyversions/{package_name}.svg)',
    # pepy.tech direct badge
    BadgeType.DOWNLOADS: '[![Downloads](https://static.pepy.tech/personalized-badge/{package_name}?period=month&units=international_system&left_color=black&right_color=orange&left_text=PyPI%20downloads%20per%20month)](https://pepy.tech/project/{package_name})',
    # CodeFactor direct badge
    BadgeType.CODEFACTOR: '[![CodeFactor](https://www.codefactor.io/repository/github/{github_owner}/{github_repo}/badge)](https://www.codefactor.io/repository/github/{github_owner}/{github_repo})',
}

# Patterns to detect if a badge already exists in README
# These patterns look for actual badge markdown syntax: ![...](...)
# They avoid matching documentation text that merely mentions badge names
BADGE_DETECTION_PATTERNS = {
    # Look for badge image markdown with shields.io endpoint containing synced/rhiza keywords
    BadgeType.SYNCED_WITH_RHIZA: r'!\[.*\]\([^)]*(?:synced.*rhiza|synced%20with.*rhiza)[^)]*\)',
    # Look for coverage badge image markdown (shields.io endpoint or direct badge)
    BadgeType.COVERAGE: r'!\[.*[Cc]overage.*\]\([^)]*(?:shields\.io|badge)[^)]*\)',
    # Look for PyPI badge image markdown
    BadgeType.PYPI_VERSION: r'!\[.*[Pp]y[Pp][Ii].*\]\([^)]*(?:shields\.io|pypi)[^)]*\)',
    # Look for license badge image markdown (linked to LICENSE file or shields.io)
    BadgeType.LICENSE: r'!\[.*[Ll]icense.*\]\([^)]*(?:shields\.io|badge)[^)]*\)',
    # Look for Python versions badge image markdown
    BadgeType.PYTHON_VERSIONS: r'!\[.*[Pp]ython.*\]\([^)]*(?:shields\.io|badge)[^)]*\)',
    # Look for downloads badge (pepy.tech or shields.io)
    BadgeType.DOWNLOADS: r'!\[.*[Dd]ownload.*\]\([^)]*(?:pepy\.tech|shields\.io)[^)]*\)',
    # Look for CodeFactor badge image markdown
    BadgeType.CODEFACTOR: r'!\[.*[Cc]ode[Ff]actor.*\]\([^)]*(?:codefactor\.io|shields\.io)[^)]*\)',
}


def get_badge_markdown(
    badge_type: BadgeType,
    badge_url: str,
    config: BadgeConfig,
) -> str:
    """Generate markdown for a badge.

    Args:
        badge_type: The type of badge.
        badge_url: URL to the badge JSON endpoint.
        config: Badge configuration with package info.

    Returns:
        Markdown string for the badge.
    """
    template = BADGE_MARKDOWN_TEMPLATES.get(badge_type, '')
    if not template:
        return ''

    # Build link URL for coverage (points to HTML report)
    coverage_link = badge_url.replace('coverage-badge.json', 'html-coverage/index.html')

    return template.format(
        badge_url=badge_url,
        link_url=coverage_link,
        package_name=config.package_name or 'package',
        license_type=config.license_type or 'MIT',
        github_owner=config.github_owner or 'owner',
        github_repo=config.github_repo or 'repo',
    )


def strip_code_blocks(content: str) -> str:
    """Remove fenced code blocks from markdown content.

    This prevents false positive matches on example badge syntax in documentation.

    Args:
        content: Markdown content.

    Returns:
        Content with code blocks removed.
    """
    # Remove fenced code blocks (```...```)
    content = re.sub(r'```[\s\S]*?```', '', content)
    # Remove inline code (`...`)
    content = re.sub(r'`[^`]+`', '', content)
    return content


def badge_exists_in_readme(badge_type: BadgeType, readme_content: str) -> bool:
    """Check if a badge already exists in the README content.

    Args:
        badge_type: The type of badge to check for.
        readme_content: The README content.

    Returns:
        True if the badge appears to exist, False otherwise.
    """
    pattern = BADGE_DETECTION_PATTERNS.get(badge_type)
    if not pattern:
        return False
    # Strip code blocks to avoid matching example badges in documentation
    content_without_code = strip_code_blocks(readme_content)
    return bool(re.search(pattern, content_without_code, re.IGNORECASE))


def find_badge_insertion_point(readme_content: str) -> int:
    """Find the best position to insert badges in README.

    Looks for existing badges or the first heading, and inserts after.

    Args:
        readme_content: The README content.

    Returns:
        Index position where badges should be inserted.
    """
    lines = readme_content.split('\n')

    # Look for existing badge line (contains shields.io or badge patterns)
    badge_pattern = re.compile(r'!\[.*\]\(.*(?:shields\.io|badge|img\.shields).*\)', re.IGNORECASE)

    last_badge_line = -1
    first_heading_line = -1

    for i, line in enumerate(lines):
        if badge_pattern.search(line):
            last_badge_line = i
        if first_heading_line == -1 and line.startswith('#'):
            first_heading_line = i

    # If we found existing badges, insert after the last one
    if last_badge_line >= 0:
        # Find the end of this line in the original content
        pos = 0
        for i, line in enumerate(lines):
            if i == last_badge_line:
                return pos + len(line) + 1  # +1 for newline
            pos += len(line) + 1

    # Otherwise, insert after the first heading
    if first_heading_line >= 0:
        pos = 0
        for i, line in enumerate(lines):
            if i == first_heading_line:
                return pos + len(line) + 1
            pos += len(line) + 1

    # Fallback: insert at the beginning
    return 0


def extract_existing_badge(badge_type: BadgeType, readme_content: str) -> str | None:
    """Extract existing badge markdown from README if present.

    Args:
        badge_type: The type of badge to extract.
        readme_content: The README content (with code blocks already stripped).

    Returns:
        The existing badge markdown string, or None if not found.
    """
    pattern = BADGE_DETECTION_PATTERNS.get(badge_type)
    if not pattern:
        return None

    # For linked badges [![...](...)], we need to match the full pattern
    # Try to match [![alt](img)](link) first, then ![alt](img)
    linked_pattern = rf'\[{pattern}\]\([^)]+\)'
    match = re.search(linked_pattern, readme_content, re.IGNORECASE)
    if match:
        return match.group(0)

    # Try simple image pattern
    match = re.search(pattern, readme_content, re.IGNORECASE)
    if match:
        return match.group(0)

    return None


def update_badges_in_readme(
    badges_to_update: list[tuple[BadgeType, str]],
    readme_path: Path,
    config: BadgeConfig,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Add or update badge markdown in README.

    Compares new badge markdown with existing badges. If different, updates in place.
    If not present, adds to the badge section.

    Args:
        badges_to_update: List of (badge_type, badge_url) tuples.
        readme_path: Path to README.md file.
        config: Badge configuration.
        dry_run: If True, print what would happen.

    Returns:
        Tuple of (badges_added, badges_updated).
    """
    if not readme_path.exists():
        logger.warning(f"README not found at {readme_path}")
        return 0, 0

    readme_content = readme_path.read_text()
    content_without_code = strip_code_blocks(readme_content)

    badges_added = []
    badges_updated = []
    new_content = readme_content

    for badge_type, badge_url in badges_to_update:
        new_markdown = get_badge_markdown(badge_type, badge_url, config)
        if not new_markdown:
            continue

        existing_badge = extract_existing_badge(badge_type, content_without_code)

        if existing_badge:
            # Badge exists - check if it needs updating
            if existing_badge.strip() != new_markdown.strip():
                # Find and replace in actual content (not stripped version)
                if existing_badge in new_content:
                    new_content = new_content.replace(existing_badge, new_markdown, 1)
                    badges_updated.append((badge_type, existing_badge, new_markdown))
                    logger.debug(f"Updated {badge_type.value} badge")
            else:
                logger.debug(f"Badge {badge_type.value} unchanged, skipping")
        else:
            # Badge doesn't exist - add it
            badges_added.append(new_markdown)

    # Add new badges if any
    if badges_added:
        insert_pos = find_badge_insertion_point(new_content)
        badge_block = '\n'.join(badges_added) + '\n'
        new_content = new_content[:insert_pos] + badge_block + new_content[insert_pos:]

    # Report changes
    if dry_run:
        if badges_updated:
            typer.echo(f"\nWould update in {readme_path}:")
            for badge_type, old, new in badges_updated:
                typer.echo(f"  {badge_type.value}:")
                typer.echo(f"    - {old[:60]}...")
                typer.echo(f"    + {new[:60]}...")
        if badges_added:
            typer.echo(f"\nWould add to {readme_path}:")
            for badge in badges_added:
                typer.echo(f"  {badge}")
    else:
        if badges_updated or badges_added:
            readme_path.write_text(new_content)
            if badges_updated:
                logger.info(f"Updated {len(badges_updated)} badge(s) in {readme_path}")
            if badges_added:
                logger.info(f"Added {len(badges_added)} badge(s) to {readme_path}")

    return len(badges_added), len(badges_updated)


def generate_badges_command(
    output_dir: Path | None = None,
    badges: list[str] | None = None,
    all_badges: bool = False,
    update_readme: bool = False,
    readme_path: Path | None = None,
    badge_url_base: str | None = None,
    dry_run: bool = False,
) -> None:
    """Generate badge endpoint JSON files for shields.io.

    Args:
        output_dir: Path to output directory.
        badges: List of badge names to generate.
        all_badges: Generate all available badges.
        update_readme: Add or update badges in README.md.
        readme_path: Path to README.md file.
        badge_url_base: Base URL for hosted badges.
        dry_run: If True, print what would happen without writing files.
    """
    # Build list of badges to generate
    badges_to_generate: list[BadgeType] = []

    if all_badges:
        badges_to_generate = list(BadgeType)
    elif badges:
        # Parse badge names from the list
        # Handle both ["a,b,c"] and ["a", "b", "c"] formats
        badge_names: list[str] = []
        for item in badges:
            badge_names.extend(name.strip() for name in item.split(","))

        for name in badge_names:
            try:
                badge_type = BadgeType(name)
                if badge_type not in badges_to_generate:
                    badges_to_generate.append(badge_type)
            except ValueError:
                typer.echo(f"⚠ Unknown badge type: {name}", err=True)
                typer.echo(
                    f"  Available: {', '.join(b.value for b in BadgeType)}", err=True
                )
    # If no badges specified, get_badge_config will read from config file

    config = get_badge_config(output_dir, badges_to_generate if badges_to_generate else None)

    logger.info(f"Generating badges to {config.output_dir}...")

    generated = 0
    skipped = 0
    generated_badges: list[tuple[BadgeType, str]] = []  # Track for README update

    for badge_type in config.badges:
        badge_data = None
        filename = f"{badge_type.value}.json"

        if badge_type == BadgeType.SYNCED_WITH_RHIZA:
            badge_data = generate_synced_with_rhiza_badge()
            filename = "synced-with-rhiza.json"
        elif badge_type == BadgeType.COVERAGE:
            badge_data = generate_coverage_badge(
                config.coverage_json,
                config.coverage_thresholds,
            )
            filename = config.coverage_filename
        elif badge_type == BadgeType.PYPI_VERSION:
            badge_data = generate_pypi_version_badge(config.package_name)
            filename = "pypi-version.json"
        elif badge_type == BadgeType.LICENSE:
            badge_data = generate_license_badge(config.license_type)
            filename = "license.json"
        elif badge_type == BadgeType.PYTHON_VERSIONS:
            badge_data = generate_python_versions_badge(config.python_versions)
            filename = "python-versions.json"
        elif badge_type == BadgeType.DOWNLOADS:
            badge_data = generate_downloads_badge(config.package_name)
            filename = "downloads.json"
        elif badge_type == BadgeType.CODEFACTOR:
            badge_data = generate_codefactor_badge(
                config.github_owner,
                config.github_repo,
            )
            filename = "codefactor.json"

        if badge_data:
            output_path = config.output_dir / filename
            if write_badge(badge_data, output_path, dry_run):
                generated += 1
                # Build URL for this badge
                if badge_url_base:
                    badge_url = f"{badge_url_base.rstrip('/')}/{filename}"
                else:
                    badge_url = str(output_path)
                generated_badges.append((badge_type, badge_url))
                if not dry_run:
                    logger.info(f"Generated {badge_type.value} badge: {output_path}")
        else:
            skipped += 1
            logger.debug(f"Skipped {badge_type.value} badge (missing data)")

    if dry_run:
        typer.echo(f"\nWould generate {generated} badge(s), skip {skipped}")
    else:
        typer.echo(f"✓ Generated {generated} badge(s), skipped {skipped}")

    # Update badges in README if requested
    if update_readme and generated_badges:
        resolved_readme = readme_path or Path("README.md")
        if not badge_url_base:
            typer.echo(
                "\n⚠ Warning: --badge-url-base not specified. "
                "Badge URLs will use local paths."
            )
        added, updated = update_badges_in_readme(
            generated_badges,
            resolved_readme,
            config,
            dry_run,
        )
        if added > 0 or updated > 0:
            if dry_run:
                if added:
                    typer.echo(f"Would add {added} badge(s) to {resolved_readme}")
                if updated:
                    typer.echo(f"Would update {updated} badge(s) in {resolved_readme}")
            else:
                if added:
                    typer.echo(f"✓ Added {added} badge(s) to {resolved_readme}")
                if updated:
                    typer.echo(f"✓ Updated {updated} badge(s) in {resolved_readme}")
