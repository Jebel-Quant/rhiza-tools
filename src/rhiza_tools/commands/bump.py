"""Command to bump version in pyproject.toml using semver and bump-my-version.

This module implements version bumping functionality with support for semantic
versioning, interactive selection, and various bump types (patch, minor, major,
prerelease variants).

Example:
    Bump to a specific version::

        from rhiza_tools.commands.bump import bump_command
        bump_command("1.2.3")

    Bump patch version with commit::

        bump_command("patch", commit=True)

    Interactive bump (no version specified)::

        bump_command(None)
"""

from pathlib import Path
from typing import Any

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
    """Read current version from pyproject.toml.

    Returns:
        The current version string from the project.version field.

    Raises:
        typer.Exit: If pyproject.toml cannot be read or parsed.

    Example:
        >>> version = get_current_version()  # doctest: +SKIP
        >>> print(version)  # doctest: +SKIP
        0.1.0
    """
    try:
        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())
            return data["project"]["version"]
    except Exception as e:
        logger.error(f"Failed to read version from pyproject.toml: {e}")
        raise typer.Exit(code=1) from None


def get_next_prerelease(current_version: semver.Version, token: str) -> semver.Version:
    """Calculate next prerelease version for a given token.

    Args:
        current_version: The current semantic version.
        token: The prerelease token (e.g., "alpha", "beta", "rc", "dev").

    Returns:
        The next prerelease version with the specified token.

    Example:
        >>> import semver
        >>> current = semver.Version.parse("1.0.0")
        >>> next_alpha = get_next_prerelease(current, "alpha")
        >>> print(next_alpha)
        1.0.1-alpha.1
    """
    if current_version.prerelease:
        if current_version.prerelease.startswith(token):
            return current_version.bump_prerelease()
        else:
            return current_version.replace(prerelease=f"{token}.1")
    else:
        return current_version.bump_patch().bump_prerelease(token=token)


def _determine_bump_type_from_choice(choice: str) -> str:
    """Extract bump type from interactive choice string.

    Args:
        choice: The choice string selected by the user (e.g., "Patch (1.0.0 -> 1.0.1)").

    Returns:
        The bump type extracted from the choice prefix (e.g., "patch").

    Example:
        >>> bump_type = _determine_bump_type_from_choice("Patch (1.0.0 -> 1.0.1)")
        >>> print(bump_type)
        patch
    """
    for prefix, bump_type in _CHOICE_PREFIX_TO_BUMP_TYPE.items():
        if choice.startswith(prefix):
            return bump_type
    return ""


def _get_interactive_bump_type(config) -> str:
    """Get bump type from user through interactive prompt.

    Displays an interactive menu with all available bump types and their
    resulting versions. Returns the selected new version string.

    Args:
        config: The bumpversion configuration object containing current_version.

    Returns:
        The new version string selected by the user.

    Raises:
        typer.Exit: If the current version is invalid or user cancels selection.

    Example:
        Interactive prompt shows::

            Select bump type (Current: 1.0.0)
            > Patch (1.0.0 -> 1.0.1)
              Minor (1.0.0 -> 1.1.0)
              Major (1.0.0 -> 2.0.0)
              ...
    """
    current_version_str = config.current_version
    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        logger.error(f"Invalid semantic version in configuration: {current_version_str}")
        raise typer.Exit(code=1) from None

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

    Converts bump type keywords (patch, minor, major, etc.) to explicit version
    strings, or validates and returns explicit version strings.

    Args:
        version: The version argument provided by the user. Can be a bump type
            keyword or an explicit version string.
        current_version_str: The current version string.

    Returns:
        The explicit version string to bump to, or empty string if version is None.

    Raises:
        typer.Exit: If the version format is invalid.

    Example:
        >>> version = _parse_version_argument("patch", "1.0.0")
        >>> print(version)
        1.0.1

        >>> version = _parse_version_argument("2.0.0", "1.0.0")
        >>> print(version)
        2.0.0
    """
    if not version:
        return ""

    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        logger.error(f"Invalid semantic version: {current_version_str}")
        raise typer.Exit(code=1) from None

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
        raise typer.Exit(code=1) from None

    return version


def _validate_pyproject_exists():
    """Validate that pyproject.toml exists in the current directory.

    Raises:
        typer.Exit: If pyproject.toml is not found.
    """
    if not Path("pyproject.toml").exists():
        logger.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)


def _build_configuration(current_version_str: str, allow_dirty: bool, commit: bool) -> tuple[Any, Path]:
    """Build bumpversion configuration with appropriate overrides.

    Args:
        current_version_str: The current version string.
        allow_dirty: If True, allow bumping even with uncommitted changes.
        commit: If True, automatically commit the version change to git.

    Returns:
        A tuple of (config object, config_path).

    Raises:
        typer.Exit: If configuration loading fails.
    """
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
        raise typer.Exit(code=1) from None
    else:
        return config, config_path


def _execute_bump(new_version_str: str, config: Any, config_path: Path, dry_run: bool, verbose: bool):
    """Execute the bump operation using bump-my-version.

    Args:
        new_version_str: The new version string to bump to.
        config: The bumpversion configuration object.
        config_path: Path to the bumpversion configuration file.
        dry_run: If True, show what would change without actually changing anything.
        verbose: If True, show detailed output from the bump-my-version tool.

    Raises:
        typer.Exit: If the bump operation fails.
    """
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
        raise typer.Exit(code=1) from None


def _log_bump_success(current_version_str: str):
    """Log successful version bump and post-bump instructions.

    Args:
        current_version_str: The original version string before the bump.
    """
    updated_version = get_current_version()
    logger.success(f"Version bumped: {current_version_str} -> {updated_version}")
    logger.info("Don't forget to run 'uv lock' to update the lockfile if needed.")


def bump_command(
    version: str | None = None,
    dry_run: bool = False,
    commit: bool = False,
    allow_dirty: bool = False,
    verbose: bool = False,
):
    """Bump version in pyproject.toml using bump-my-version.

    This function handles the complete version bumping workflow including
    configuration loading, version parsing, interactive selection (if needed),
    and executing the bump operation.

    Args:
        version: The version to bump to. Can be an explicit version (e.g., "1.2.3"),
            a bump type ("patch", "minor", "major"), a prerelease type
            ("alpha", "beta", "rc", "dev"), or None for interactive selection.
        dry_run: If True, show what would change without actually changing anything.
        commit: If True, automatically commit the version change to git.
        allow_dirty: If True, allow bumping even with uncommitted changes.
        verbose: If True, show detailed output from the bump-my-version tool.

    Raises:
        typer.Exit: If pyproject.toml is missing, configuration is invalid, or
            bump operation fails.

    Example:
        Bump to patch version::

            bump_command("patch")

        Bump with dry run::

            bump_command("1.2.3", dry_run=True)

        Interactive bump with commit::

            bump_command(None, commit=True)
    """
    _validate_pyproject_exists()

    current_version_str = get_current_version()
    config, config_path = _build_configuration(current_version_str, allow_dirty, commit)

    logger.info(f"Current version: {typer.style(current_version_str, fg=typer.colors.CYAN, bold=True)}")

    # Determine new version string
    if version:
        new_version_str = _parse_version_argument(version, current_version_str)
    else:
        new_version_str = _get_interactive_bump_type(config)

    logger.info(f"New version will be: {new_version_str}")

    _execute_bump(new_version_str, config, config_path, dry_run, verbose)

    if not dry_run:
        _log_bump_success(current_version_str)
