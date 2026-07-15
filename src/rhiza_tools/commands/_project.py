"""Project-metadata and version helpers shared across rhiza-tools commands.

This module owns the ``pyproject.toml``-facing and semver-parsing helpers used
by the bump and release flows:

    - get_current_version: Read the project version from pyproject.toml.
    - parse_semver_or_exit: Parse a semver string, exiting consistently on error.
    - validate_pyproject_exists: Guard against a missing pyproject.toml.
"""

import tomllib
from pathlib import Path

import semver
import typer

from rhiza_tools import console


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
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        return str(data["project"]["version"])
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as e:
        console.error(f"Failed to read version from pyproject.toml: {e}")
        raise typer.Exit(code=1) from None


def parse_semver_or_exit(version_str: str, *, strip_v_prefix: bool = False) -> semver.Version:
    """Parse a semantic version string, exiting with a consistent error on failure.

    Centralises the parse-and-exit pattern that several commands previously
    duplicated, so an unparseable version is always reported the same way.

    Args:
        version_str: The version to parse (e.g. ``"1.2.3"`` or ``"v1.2.3"``).
        strip_v_prefix: If True, drop a leading ``"v"`` before parsing.

    Returns:
        The parsed :class:`semver.Version`.

    Raises:
        typer.Exit: If ``version_str`` is not a valid semantic version.

    Example:
        >>> parse_semver_or_exit("1.2.3")  # doctest: +SKIP
        Version(major=1, minor=2, patch=3, ...)
    """
    candidate = version_str[1:] if strip_v_prefix and version_str.startswith("v") else version_str
    try:
        return semver.Version.parse(candidate)
    except ValueError:
        console.error(f"Invalid semantic version: {version_str}")
        raise typer.Exit(code=1) from None


def validate_pyproject_exists() -> None:
    """Validate that pyproject.toml exists in the current directory.

    Raises:
        typer.Exit: If pyproject.toml is not found.
    """
    if not Path("pyproject.toml").exists():
        console.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)
