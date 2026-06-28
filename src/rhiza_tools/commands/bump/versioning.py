"""Pure version-math helpers for the bump command.

This module contains the version-arithmetic building blocks used by the bump
command: PEP 440 / semver normalization, prerelease calculation, bump-type
resolution, and version-argument parsing. It deliberately contains no
interactive (``questionary``) code and no bump-my-version integration so the
version logic can be reasoned about and tested in isolation.
"""

from collections.abc import Callable

import semver
import typer

from rhiza_tools import console
from rhiza_tools.commands._shared import parse_semver_or_exit


def _denormalize_pep440_to_semver(version_str: str) -> str:
    """Convert PEP 440 prerelease format to semver format.

    Converts PEP 440 format (e.g., 0.1.1a1 or 0.1.1alpha1) back to semver format
    (e.g., 0.1.1-alpha.1) for compatibility with the semver library and bump-my-version.

    Args:
        version_str: Version string, possibly in PEP 440 format.

    Returns:
        Version string in semver format.

    Example:
        >>> _denormalize_pep440_to_semver("0.1.1a1")
        '0.1.1-alpha.1'
        >>> _denormalize_pep440_to_semver("0.1.1alpha1")
        '0.1.1-alpha.1'
        >>> _denormalize_pep440_to_semver("0.1.1")
        '0.1.1'
    """
    import re

    # Pattern to match PEP 440 prerelease: 0.1.1a1, 0.1.1alpha1, 0.1.1b2, 0.1.1rc3
    # Captures: major.minor.patch, release letter(s), and pre_n
    pattern = r"^(\d+\.\d+\.\d+)(a|alpha|b|beta|rc|dev)(\d+)$"
    match = re.match(pattern, version_str)

    if match:
        base, release_short, pre_n = match.groups()
        # Map PEP 440 forms to full names for semver
        release_map = {
            "a": "alpha",
            "alpha": "alpha",
            "b": "beta",
            "beta": "beta",
            "rc": "rc",
            "dev": "dev",
        }
        release_full = release_map.get(release_short, release_short)
        return f"{base}-{release_full}.{pre_n}"

    # If not a PEP 440 prerelease, return as-is
    return version_str


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


def get_bumped_version_from_type(current_version: semver.Version, version_type: str) -> str:
    """Get bumped version string from version type keyword.

    Args:
        current_version: The current semantic version.
        version_type: The bump type keyword.

    Returns:
        The bumped version string.
    """
    bump_mapping: dict[str, Callable[[], semver.Version]] = {
        "patch": current_version.bump_patch,
        "minor": current_version.bump_minor,
        "major": current_version.bump_major,
        "prerelease": current_version.bump_prerelease,
        "build": current_version.bump_build,
    }

    if version_type in bump_mapping:
        return str(bump_mapping[version_type]())
    elif version_type in ["alpha", "beta", "rc", "dev"]:
        return str(get_next_prerelease(current_version, version_type))

    return ""


def _validate_explicit_version(version: str) -> str:
    """Validate and clean explicit version string.

    Args:
        version: Version string to validate.

    Returns:
        Cleaned version string.

    Raises:
        typer.Exit: If version format is invalid.
    """
    # Strip 'v' prefix
    cleaned_version = version[1:] if version.startswith("v") else version

    # Validate explicit version
    try:
        semver.Version.parse(cleaned_version)
    except ValueError:
        console.error(f"Invalid version format: {version}")
        console.error("Please use a valid semantic version.")
        raise typer.Exit(code=1) from None

    return cleaned_version


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

    current_version = parse_semver_or_exit(current_version_str)

    # Try to get bumped version from type keyword
    bumped_version = get_bumped_version_from_type(current_version, version)
    if bumped_version:
        return bumped_version

    # Otherwise, it's an explicit version - validate and return
    return _validate_explicit_version(version)
