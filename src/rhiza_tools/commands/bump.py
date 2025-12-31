"""Command to bump version in pyproject.toml using semver and tomlkit."""

from pathlib import Path

import questionary as qs
import semver
import tomlkit
import typer
from loguru import logger

_COOL_STYLE = qs.Style(
    [
        ("separator", "fg:#cc5454"),
        ("qmark", "fg:#2FA4A9 bold"),
        ("question", ""),
        ("selected", "fg:#2FA4A9 bold"),
        ("pointer", "fg:#2FA4A9 bold"),
        ("highlighted", "fg:#2FA4A9 bold"),
        ("answer", "fg:#2FA4A9 bold"),
        ("text", "fg:#ffffff"),
        ("disabled", "fg:#858585 italic"),
    ]
)

# Valid bump type keywords
_VALID_BUMP_TYPES = ["patch", "minor", "major", "prerelease", "build", "alpha", "beta", "rc", "dev"]

# Mapping of choice prefix to bump type for interactive selection
_CHOICE_PREFIX_TO_BUMP_TYPE = {
    "Patch": "patch",
    "Minor": "minor",
    "Major": "major",
    "Alpha": "alpha",
    "Beta": "beta",
    "RC": "rc",
    "Dev": "dev",
    "Prerelease": "prerelease",
    "Build": "build",
}


def get_current_version() -> str:
    """Read current version from pyproject.toml."""
    try:
        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())
            return data["project"]["version"]
    except Exception as e:
        logger.error(f"Failed to read version from pyproject.toml: {e}")
        raise typer.Exit(code=1)


def update_version(new_version: str) -> None:
    """Update version in pyproject.toml."""
    try:
        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())

        data["project"]["version"] = new_version

        with open("pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(data))

    except Exception as e:
        logger.error(f"Failed to update pyproject.toml: {e}")
        raise typer.Exit(code=1)


def get_next_prerelease(current_version: semver.Version, token: str) -> semver.Version:
    """Calculate next prerelease version for a given token."""
    if current_version.prerelease:
        if current_version.prerelease.startswith(token):
            return current_version.bump_prerelease()
        else:
            return current_version.replace(prerelease=f"{token}.1")
    else:
        return current_version.bump_patch().bump_prerelease(token=token)


def _determine_bump_type_from_choice(choice: str) -> str:
    """Extract bump type from interactive choice string."""
    for prefix, bump_type in _CHOICE_PREFIX_TO_BUMP_TYPE.items():
        if choice.startswith(prefix):
            return bump_type
    return ""


def _get_interactive_bump_type(current_version: semver.Version) -> str:
    """Get bump type from user through interactive prompt."""
    next_patch = current_version.bump_patch()
    next_minor = current_version.bump_minor()
    next_major = current_version.bump_major()
    next_prerelease = current_version.bump_prerelease()
    next_build = current_version.bump_build()

    next_alpha = get_next_prerelease(current_version, "alpha")
    next_beta = get_next_prerelease(current_version, "beta")
    next_rc = get_next_prerelease(current_version, "rc")
    next_dev = get_next_prerelease(current_version, "dev")

    current_version_str = str(current_version)
    choice = qs.select(
        f"Select bump type (Current: {current_version_str})",
        choices=[
            f"Patch ({current_version_str} -> {next_patch})",
            f"Minor ({current_version_str} -> {next_minor})",
            f"Major ({current_version_str} -> {next_major})",
            qs.Separator("-" * 30),
            f"Prerelease ({current_version_str} -> {next_prerelease})",
            f"Alpha ({current_version_str} -> {next_alpha})",
            f"Beta ({current_version_str} -> {next_beta})",
            f"RC ({current_version_str} -> {next_rc})",
            f"Dev ({current_version_str} -> {next_dev})",
            f"Build ({current_version_str} -> {next_build})",
        ],
        style=_COOL_STYLE,
    ).ask()

    if not choice:
        raise typer.Exit(code=0)

    return _determine_bump_type_from_choice(choice)


def _parse_version_argument(version: str | None) -> tuple[str, str]:
    """Parse version argument and return (bump_type, explicit_version).

    Returns:
        A tuple of (bump_type, explicit_version) where one will be empty string.
    """
    if not version:
        return ("", "")

    # Check if it's a bump type keyword
    if version in _VALID_BUMP_TYPES:
        return (version, "")

    # Otherwise, it's an explicit version
    # Strip 'v' prefix
    if version.startswith("v"):
        version = version[1:]
    return ("", version)


def _calculate_new_version(current_version: semver.Version, bump_type: str, explicit_version: str) -> str:
    """Calculate the new version based on bump type or explicit version."""
    if bump_type:
        logger.info(f"Bumping version using: {bump_type}")
        if bump_type == "patch":
            return str(current_version.bump_patch())
        elif bump_type == "minor":
            return str(current_version.bump_minor())
        elif bump_type == "major":
            return str(current_version.bump_major())
        elif bump_type == "prerelease":
            return str(current_version.bump_prerelease())
        elif bump_type == "build":
            return str(current_version.bump_build())
        elif bump_type in ["alpha", "beta", "rc", "dev"]:
            return str(get_next_prerelease(current_version, bump_type))
        else:
            # This should never happen if _parse_version_argument is working correctly
            logger.error(f"Unknown bump type: {bump_type}")
            raise typer.Exit(code=1)
    elif explicit_version:
        # Validate explicit version
        try:
            semver.Version.parse(explicit_version)
        except ValueError:
            logger.error(f"Invalid version format: {explicit_version}")
            logger.error("Please use a valid semantic version.")
            raise typer.Exit(code=1)
        return explicit_version
    else:
        # This should never happen if the calling code is correct
        logger.error("No bump type or explicit version provided")
        raise typer.Exit(code=1)


def bump_command(version: str | None = None, dry_run: bool = False):
    """Bump version in pyproject.toml using semver and tomlkit."""
    # Check if pyproject.toml exists
    if not Path("pyproject.toml").exists():
        logger.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)

    # Get current version
    current_version_str = get_current_version()
    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        logger.error(f"Invalid semantic version in pyproject.toml: {current_version_str}")
        raise typer.Exit(code=1)

    logger.info(f"Current version: {typer.style(current_version_str, fg=typer.colors.CYAN, bold=True)}")

    # Determine bump type and explicit version
    if version:
        bump_type, explicit_version = _parse_version_argument(version)
    else:
        bump_type = _get_interactive_bump_type(current_version)
        explicit_version = ""

    # Calculate new version
    new_version_str = _calculate_new_version(current_version, bump_type, explicit_version)

    logger.info(f"New version will be: {new_version_str}")

    if dry_run:
        logger.info("Dry run enabled. Skipping actual changes.")
        return

    # Update version in pyproject.toml
    logger.info("Updating pyproject.toml...")
    update_version(new_version_str)

    # Verify the update
    updated_version = get_current_version()
    if updated_version != new_version_str:
        logger.error(f"Version update failed. Expected {new_version_str} but got {updated_version}")
        raise typer.Exit(code=1)

    logger.success(f"Version bumped: {current_version_str} -> {new_version_str} in pyproject.toml")
    logger.info("Don't forget to run 'uv lock' to update the lockfile if needed.")
