"""Command to bump version in pyproject.toml using semver and bump-my-version."""

from pathlib import Path

import questionary as qs
import semver
import tomlkit
import typer
from bumpversion.bump import do_bump
from bumpversion.config import get_configuration
from bumpversion.ui import setup_logging
from loguru import logger

from rhiza_tools.config import CONFIG_FILENAME

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


def _get_interactive_bump_type(config) -> str:
    """Get bump type from user through interactive prompt."""
    current_version_str = config.current_version
    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        logger.error(f"Invalid semantic version in configuration: {current_version_str}")
        raise typer.Exit(code=1)

    next_patch = current_version.bump_patch()
    next_minor = current_version.bump_minor()
    next_major = current_version.bump_major()
    next_prerelease = current_version.bump_prerelease()
    next_build = current_version.bump_build()

    next_alpha = get_next_prerelease(current_version, "alpha")
    next_beta = get_next_prerelease(current_version, "beta")
    next_rc = get_next_prerelease(current_version, "rc")
    next_dev = get_next_prerelease(current_version, "dev")

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

    # Extract the new version string from the choice
    # Format is "Label (Current -> New)"
    # We want "New"
    new_version = choice.split("-> ")[1].rstrip(")")
    return new_version


def _parse_version_argument(version: str | None, current_version_str: str) -> str:
    """Parse version argument and return explicit version string.

    Args:
        version: The version argument provided by the user.
        current_version_str: The current version string.

    Returns:
        The explicit version string to bump to.
    """
    if not version:
        return ""

    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        logger.error(f"Invalid semantic version: {current_version_str}")
        raise typer.Exit(code=1)

    # Check if it's a bump type keyword
    if version == "patch":
        return str(current_version.bump_patch())
    elif version == "minor":
        return str(current_version.bump_minor())
    elif version == "major":
        return str(current_version.bump_major())
    elif version == "prerelease":
        return str(current_version.bump_prerelease())
    elif version == "build":
        return str(current_version.bump_build())
    elif version in ["alpha", "beta", "rc", "dev"]:
        return str(get_next_prerelease(current_version, version))

    # Otherwise, it's an explicit version
    # Strip 'v' prefix
    if version.startswith("v"):
        version = version[1:]
    
    # Validate explicit version
    try:
        semver.Version.parse(version)
    except ValueError:
        logger.error(f"Invalid version format: {version}")
        logger.error("Please use a valid semantic version.")
        raise typer.Exit(code=1)
        
    return version


def bump_command(
    version: str | None = None,
    dry_run: bool = False,
    commit: bool = False,
    allow_dirty: bool = False,
    verbose: bool = False,
):
    """Bump version in pyproject.toml using bump-my-version."""
    # Check if pyproject.toml exists
    if not Path("pyproject.toml").exists():
        logger.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)

    # Get current version from pyproject.toml
    current_version_str = get_current_version()

    # Construct configuration
    config_path = Path(CONFIG_FILENAME)
    overrides = {"current_version": current_version_str}
    if allow_dirty:
        overrides["allow_dirty"] = True
    if commit:
        overrides["commit"] = True

    try:
        config = get_configuration(config_file=config_path, **overrides)
    except Exception as e:
        logger.error(f"Failed to load bumpversion configuration: {e}")
        raise typer.Exit(code=1)

    logger.info(f"Current version: {typer.style(current_version_str, fg=typer.colors.CYAN, bold=True)}")

    # Determine new version string
    if version:
        new_version_str = _parse_version_argument(version, current_version_str)
    else:
        new_version_str = _get_interactive_bump_type(config)

    logger.info(f"New version will be: {new_version_str}")

    # Run bump-my-version
    logger.info("Running bump-my-version...")
    setup_logging(verbose=1 if verbose else 0)

    try:
        do_bump(
            version_part=None,
            new_version=new_version_str,
            config=config,
            config_file=config_path,
            dry_run=dry_run,
        )
    except Exception as e:
        logger.error(f"bump-my-version failed: {e}")
        raise typer.Exit(code=1)

    if not dry_run:
        # Re-read config to get updated version
        # Note: Since we removed current_version from config file, we should read from pyproject.toml again
        updated_version = get_current_version()
        logger.success(f"Version bumped: {current_version_str} -> {updated_version}")
        logger.info("Don't forget to run 'uv lock' to update the lockfile if needed.")
