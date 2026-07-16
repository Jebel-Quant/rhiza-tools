"""Command to emit supported Python versions from pyproject.toml.

This module reads the ``Programming Language :: Python :: 3.x`` trove
classifiers declared in ``pyproject.toml`` and emits the corresponding minor
versions as a JSON array. It's primarily used in GitHub Actions to compute the
test matrix, so the matrix always mirrors exactly what the project advertises
that it supports — adding or removing a classifier changes CI coverage.

Example:
    Get supported versions as JSON::

        from rhiza_tools.commands.version_matrix import version_matrix_command
        version_matrix_command()
        # Output: ["3.11", "3.12"]
"""

import json
import re
import tomllib
from pathlib import Path

import typer
from packaging.version import InvalidVersion, Version

from rhiza_tools import console

# Matches a ``major.minor`` Python trove classifier, e.g.
# "Programming Language :: Python :: 3.11". The major-only classifier
# ("... :: 3") and suffixed variants ("... :: 3 :: Only") are intentionally
# not matched — only concrete minor versions belong in the test matrix.
_CLASSIFIER_RE = re.compile(r"^Programming Language :: Python :: (\d+\.\d+)$")


class RhizaError(Exception):
    """Base exception for Rhiza-related errors."""


class PyProjectError(RhizaError):
    """Raised when there are issues with pyproject.toml configuration."""


def get_supported_versions(pyproject_path: Path) -> list[str]:
    """Return the Python minor versions declared in pyproject.toml classifiers.

    Reads ``project.classifiers`` and extracts every
    ``Programming Language :: Python :: X.Y`` entry, returning the versions in
    ascending order.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        List of supported versions (e.g., ["3.11", "3.12"]).

    Raises:
        PyProjectError: If pyproject.toml doesn't exist or declares no
            ``Programming Language :: Python :: X.Y`` classifiers.

    Example:
        >>> from pathlib import Path
        >>> versions = get_supported_versions(Path("pyproject.toml"))  # doctest: +SKIP
        >>> print(versions)  # doctest: +SKIP
        ['3.11', '3.12']
    """
    if not pyproject_path.exists():
        msg = f"pyproject.toml not found at {pyproject_path}"
        raise PyProjectError(msg)

    # Load pyproject.toml using the tomllib standard library (Python 3.11+)
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    classifiers = data.get("project", {}).get("classifiers", [])

    # Extract the minor version from each matching classifier, de-duplicating.
    versions: set[str] = set()
    for classifier in classifiers:
        match = _CLASSIFIER_RE.match(classifier.strip())
        if match:
            versions.add(match.group(1))

    if not versions:
        msg = (
            "pyproject.toml: no 'Programming Language :: Python :: X.Y' classifiers found. "
            "Declare the supported Python versions as trove classifiers."
        )
        raise PyProjectError(msg)

    # Sort by semantic version so 3.9 orders before 3.11 (string sort would not).
    try:
        return sorted(versions, key=Version)
    except InvalidVersion as e:  # pragma: no cover - guards against malformed classifiers
        msg = f"pyproject.toml: invalid Python version in classifiers: {e}"
        raise PyProjectError(msg) from e


def version_matrix_command(pyproject_path: Path | None = None) -> None:
    """Emit the supported Python versions from pyproject.toml classifiers as JSON.

    This command reads pyproject.toml, extracts the
    ``Programming Language :: Python :: X.Y`` classifiers, and prints a JSON
    array of those versions. This is used in GitHub Actions to compute the test
    matrix.

    Args:
        pyproject_path: Path to pyproject.toml. Defaults to ./pyproject.toml.

    Raises:
        typer.Exit: If pyproject.toml is missing or declares no Python
            classifiers.

    Example:
        Get supported versions (output to stdout)::

            version_matrix_command()
            # Output: ["3.11", "3.12"]

        Use a custom pyproject.toml path::

            version_matrix_command(pyproject_path=Path("/path/to/pyproject.toml"))
    """
    if pyproject_path is None:
        pyproject_path = Path("pyproject.toml")

    try:
        versions = get_supported_versions(pyproject_path)
        print(json.dumps(versions))
    except PyProjectError as e:
        console.error(str(e))
        raise typer.Exit(code=1) from e
