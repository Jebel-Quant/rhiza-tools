"""Public data model for the bump command.

This module holds the ``Language`` enum, the ``BumpOptions`` dataclass, and the
``--language`` option parsing that together form the public data surface of the
bump command. Keeping the model here (free of any I/O, interactive prompts, or
bump-my-version internals) lets the I/O, prompt, and reporting helpers depend on
it without pulling in each other.

All symbols defined here are re-exported by ``bump/__init__.py`` so the public
import surface is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import typer

from rhiza_tools import console


class Language(StrEnum):
    """Supported programming languages for version bumping.

    Attributes:
        PYTHON: Python projects using pyproject.toml
        GO: Go projects using VERSION file with go.mod
    """

    PYTHON = "python"
    GO = "go"

    @classmethod
    def detect(cls) -> Language | None:
        """Detect the project language based on files present.

        Returns:
            Language enum if detected, None if no supported language is found.

        Example:
            >>> lang = Language.detect()  # doctest: +SKIP
            >>> if lang:
            ...     print(lang.value)  # doctest: +SKIP
            python
        """
        if Path("pyproject.toml").exists():
            return cls.PYTHON
        elif Path("go.mod").exists() and Path("VERSION").exists():
            return cls.GO
        return None

    def get_version_file(self) -> Path:
        """Get the version file path for this language.

        Returns:
            Path to the version file.

        Example:
            >>> lang = Language.PYTHON
            >>> lang.get_version_file()  # doctest: +SKIP
            PosixPath('pyproject.toml')
        """
        if self == Language.PYTHON:
            return Path("pyproject.toml")
        # Language.GO
        return Path("VERSION")


# User-facing hint listing the languages accepted by ``--language``. Defined once
# so the message stays consistent everywhere it is shown (invalid value, failed
# auto-detection).
SUPPORTED_LANGUAGES_MSG = "Supported languages: python, go"


def parse_language_option(language: str | None) -> Language | None:
    """Parse the ``--language`` CLI option into a :class:`Language`.

    Args:
        language: The raw ``--language`` value, or ``None`` when the option was
            not supplied (auto-detection happens later).

    Returns:
        The matching :class:`Language`, or ``None`` when ``language`` is ``None``.

    Raises:
        typer.Exit: If ``language`` is given but is not a supported value.
    """
    if language is None:
        return None
    try:
        return Language(language.lower())
    except ValueError:
        console.error(f"Invalid language: {language}")
        console.error(SUPPORTED_LANGUAGES_MSG)
        raise typer.Exit(code=1) from None


@dataclass
class BumpOptions:
    """Configuration options for bump command.

    Attributes:
        version: The version to bump to. Can be an explicit version, bump type, or None.
        dry_run: If True, show what would change without actually changing anything.
        commit: If True, automatically commit the version change to git.
        push: If True, push changes to remote after commit (implies commit=True).
        branch: Branch to perform the bump on (default: current branch).
        allow_dirty: If True, allow bumping even with uncommitted changes.
        language: The programming language (python or go). If None, auto-detect.
        config: Path to the .cfg.toml config file. Defaults to CONFIG_FILENAME.
    """

    version: str | None = None
    dry_run: bool = False
    commit: bool = False
    push: bool = False
    branch: str | None = None
    allow_dirty: bool = False
    language: Language | None = None
    config: Path | None = None
