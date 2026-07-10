"""Project file I/O for the bump command.

This module reads the current version from a project's version files
(``get_current_version`` and its per-language ``_read_python_version`` /
``_read_go_version`` backends) and validates that the files a language requires
are present (``_validate_project_exists``). The public data model lives in
``bump/models.py``, interactive prompts in ``bump/prompts.py``, and post-bump
reporting in ``bump/reporting.py``.

All public symbols defined here are re-exported by ``bump/__init__.py`` so the
public import surface is unchanged.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import typer

from rhiza_tools import console
from rhiza_tools.commands.bump.models import Language
from rhiza_tools.commands.bump.versioning import (
    _denormalize_pep440_to_semver,
)


def _read_python_version() -> str:
    """Read the current version from ``pyproject.toml`` in semver format.

    Returns:
        The current version string, denormalized from PEP 440 to semver.

    Raises:
        typer.Exit: If the version cannot be read or parsed.
    """
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        # Convert PEP 440 format back to semver format for compatibility
        # e.g., 0.1.1a1 -> 0.1.1-alpha.1
        return _denormalize_pep440_to_semver(str(data["project"]["version"]))
    except (OSError, tomllib.TOMLDecodeError, KeyError) as e:
        console.error(f"Failed to read version from pyproject.toml: {e}")
        raise typer.Exit(code=1) from None


def _read_go_version() -> str:
    """Read the current version from the ``VERSION`` file.

    Returns:
        The trimmed version string.

    Raises:
        typer.Exit: If the file cannot be read or is empty/whitespace-only.
    """
    try:
        with open("VERSION") as f:
            version = f.read().strip()
    except OSError as e:
        console.error(f"Failed to read version from VERSION file: {e}")
        raise typer.Exit(code=1) from None

    if not version:
        console.error("VERSION file is empty")
        raise typer.Exit(code=1)

    # Validate that the version string is not just whitespace and looks valid
    if not version or version.isspace():
        console.error("VERSION file contains only whitespace")
        raise typer.Exit(code=1)

    return version


def get_current_version(language: Language) -> str:
    """Read current version from project configuration for the specified language.

    Args:
        language: The programming language (python or go).

    Returns:
        The current version string in semver format (for compatibility with bump logic).

    Raises:
        typer.Exit: If version cannot be read or parsed.

    Example:
        >>> version = get_current_version(Language.PYTHON)  # doctest: +SKIP
        >>> print(version)  # doctest: +SKIP
        0.1.0
    """
    if language == Language.PYTHON:
        return _read_python_version()
    if language == Language.GO:
        return _read_go_version()
    console.error(f"Unsupported language: {language}")
    raise typer.Exit(code=1)


# Files each language requires, paired with the error lines to print when the
# file is missing. Driving ``_validate_project_exists`` from this table keeps the
# per-language branching flat and makes adding a language a data-only change.
_REQUIRED_PROJECT_FILES: dict[Language, tuple[tuple[str, tuple[str, ...]], ...]] = {
    Language.PYTHON: (
        (
            "pyproject.toml",
            (
                "Python project detected but pyproject.toml not found.",
                "Please create a pyproject.toml file with the current version.",
            ),
        ),
    ),
    Language.GO: (
        (
            "go.mod",
            (
                "Go language specified but go.mod not found.",
                "Please create a go.mod file for your Go project.",
            ),
        ),
        (
            "VERSION",
            (
                "Go project detected but VERSION file not found.",
                "Please create a VERSION file with the current version.",
            ),
        ),
    ),
}


def _validate_project_exists(language: Language) -> None:
    """Validate that required project files exist for the specified language.

    Args:
        language: The programming language (python or go).

    Raises:
        typer.Exit: If required project files are not found.
    """
    required = _REQUIRED_PROJECT_FILES.get(language)
    if required is None:
        console.error(f"Unsupported language: {language}")
        raise typer.Exit(code=1)

    for filename, error_lines in required:
        if not Path(filename).exists():
            for line in error_lines:
                console.error(line)
            raise typer.Exit(code=1)
