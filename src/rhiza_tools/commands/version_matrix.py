"""Command to emit supported Python versions from pyproject.toml.

This module implements functionality to parse pyproject.toml and determine which
Python versions are supported based on the requires-python specifier. It's
primarily used in GitHub Actions to compute the test matrix.

Example:
    Get supported versions as JSON::

        from rhiza_tools.commands.version_matrix import version_matrix_command
        version_matrix_command()
        # Output: ["3.11", "3.12"]

    Use with custom candidates::

        version_matrix_command(candidates=["3.11", "3.12", "3.13", "3.14"])
"""

import json
import re
import sys
import tomllib
from pathlib import Path

from rhiza_tools import console


class RhizaError(Exception):
    """Base exception for Rhiza-related errors."""


class VersionSpecifierError(RhizaError):
    """Raised when a version string or specifier is invalid."""


class PyProjectError(RhizaError):
    """Raised when there are issues with pyproject.toml configuration."""


def parse_version(v: str) -> tuple[int, ...]:
    """Parse a version string into a tuple of integers.

    This is intentionally simple and only supports numeric components.
    If a component contains non-numeric suffixes (e.g. '3.11.0rc1'),
    the leading numeric portion will be used (e.g. '0rc1' -> 0). If a
    component has no leading digits at all, a VersionSpecifierError is raised.

    Args:
        v: Version string to parse (e.g., "3.11", "3.11.0rc1").

    Returns:
        Tuple of integers representing the version.

    Raises:
        VersionSpecifierError: If a version component has no numeric prefix.

    Example:
        >>> parse_version("3.11")
        (3, 11)

        >>> parse_version("3.11.0rc1")
        (3, 11, 0)
    """
    parts: list[int] = []
    for part in v.split("."):
        match = re.match(r"\d+", part)
        if not match:
            msg = f"Invalid version component {part!r} in version {v!r}; expected a numeric prefix."
            raise VersionSpecifierError(msg)
        parts.append(int(match.group(0)))
    return tuple(parts)


def _check_operator(version_tuple: tuple[int, ...], op: str, spec_v_tuple: tuple[int, ...]) -> bool:
    """Check if a version tuple satisfies an operator constraint.

    Args:
        version_tuple: The version to check as a tuple of integers.
        op: The comparison operator (>=, <=, >, <, ==, !=).
        spec_v_tuple: The specification version as a tuple of integers.

    Returns:
        True if the version satisfies the operator constraint, False otherwise.

    Example:
        >>> _check_operator((3, 11), ">=", (3, 10))
        True

        >>> _check_operator((3, 9), ">=", (3, 10))
        False
    """
    if op == ">=":
        return version_tuple >= spec_v_tuple
    elif op == "<=":
        return version_tuple <= spec_v_tuple
    elif op == ">":
        return version_tuple > spec_v_tuple
    elif op == "<":
        return version_tuple < spec_v_tuple
    elif op == "==":
        return version_tuple == spec_v_tuple
    elif op == "!=":
        return version_tuple != spec_v_tuple
    else:
        msg = f"Unknown operator: {op}"
        raise VersionSpecifierError(msg)


def satisfies(version: str, specifier: str) -> bool:
    """Check if a version satisfies a comma-separated list of specifiers.

    This is a simplified version of packaging.specifiers.SpecifierSet.
    Supported operators: >=, <=, >, <, ==, !=

    Args:
        version: Version string to check (e.g., "3.11").
        specifier: Comma-separated specifier string (e.g., ">=3.11,<3.14").

    Returns:
        True if the version satisfies all specifiers, False otherwise.

    Raises:
        VersionSpecifierError: If the specifier format is invalid.

    Example:
        >>> satisfies("3.11", ">=3.11")
        True

        >>> satisfies("3.10", ">=3.11")
        False

        >>> satisfies("3.12", ">=3.11,<3.14")
        True
    """
    version_tuple = parse_version(version)

    # Split by comma for multiple constraints
    for spec in specifier.split(","):
        spec = spec.strip()
        # Match operator and version part
        match = re.match(r"(>=|<=|>|<|==|!=)\s*([\d.]+)", spec)
        if not match:
            # If no operator, assume ==
            if re.match(r"[\d.]+", spec):
                if version_tuple != parse_version(spec):
                    return False
                continue
            msg = f"Invalid specifier {spec!r}; expected format like '>=3.11' or '3.11'"
            raise VersionSpecifierError(msg)

        op, spec_v = match.groups()
        spec_v_tuple = parse_version(spec_v)

        if not _check_operator(version_tuple, op, spec_v_tuple):
            return False

    return True


def get_supported_versions(pyproject_path: Path, candidates: list[str]) -> list[str]:
    """Return all supported Python versions declared in pyproject.toml.

    Reads project.requires-python, evaluates candidate versions against the
    specifier, and returns the subset that satisfy the constraint, in ascending order.

    Args:
        pyproject_path: Path to the pyproject.toml file.
        candidates: List of candidate Python versions to check (e.g., ["3.11", "3.12"]).

    Returns:
        List of supported versions (e.g., ["3.11", "3.12"]).

    Raises:
        PyProjectError: If pyproject.toml doesn't exist, requires-python is missing,
            or no candidates match.

    Example:
        >>> from pathlib import Path
        >>> path = Path("pyproject.toml")
        >>> candidates = ["3.11", "3.12", "3.13"]
        >>> versions = get_supported_versions(path, candidates)  # doctest: +SKIP
        >>> print(versions)  # doctest: +SKIP
        ['3.11', '3.12']
    """
    if not pyproject_path.exists():
        msg = f"pyproject.toml not found at {pyproject_path}"
        raise PyProjectError(msg)

    # Load pyproject.toml using the tomllib standard library (Python 3.11+)
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    # Extract the requires-python field from project metadata
    # This specifies the Python version constraint (e.g., ">=3.11")
    spec_str = data.get("project", {}).get("requires-python")
    if not spec_str:
        msg = "pyproject.toml: missing 'project.requires-python'"
        raise PyProjectError(msg)

    # Filter candidate versions to find which ones satisfy the constraint
    versions: list[str] = []
    for v in candidates:
        if satisfies(v, spec_str):
            versions.append(v)

    if not versions:
        msg = f"pyproject.toml: no supported Python versions match '{spec_str}'. Evaluated candidates: {candidates}"
        raise PyProjectError(msg)

    return versions


def version_matrix_command(
    pyproject_path: Path | None = None,
    candidates: list[str] | None = None,
) -> None:
    """Emit the list of supported Python versions from pyproject.toml as JSON.

    This command reads pyproject.toml, parses the requires-python field, and outputs
    a JSON array of Python versions that satisfy the constraint. This is used in
    GitHub Actions to compute the test matrix.

    Args:
        pyproject_path: Path to pyproject.toml. Defaults to ./pyproject.toml.
        candidates: List of candidate Python versions to evaluate. Defaults to
            ["3.11", "3.12", "3.13", "3.14"].

    Raises:
        SystemExit: If pyproject.toml is missing, invalid, or no versions match.

    Example:
        Get supported versions (output to stdout)::

            version_matrix_command()
            # Output: ["3.11", "3.12"]

        Use custom pyproject.toml path::

            version_matrix_command(pyproject_path=Path("/path/to/pyproject.toml"))

        Use custom candidates::

            version_matrix_command(candidates=["3.10", "3.11", "3.12"])
    """
    if pyproject_path is None:
        pyproject_path = Path("pyproject.toml")

    if candidates is None:
        candidates = ["3.11", "3.12", "3.13", "3.14"]

    try:
        versions = get_supported_versions(pyproject_path, candidates)
        # Output as JSON array (matches the behavior of the original script)
        print(json.dumps(versions))
    except (PyProjectError, VersionSpecifierError) as e:
        console.error(str(e))
        sys.exit(1)
