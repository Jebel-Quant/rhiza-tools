"""Project I/O and interactive UI helpers for the bump command.

This module holds the ``Language`` enum and ``BumpOptions`` dataclass (the public
data model for bump), plus the helpers that read project files
(``get_current_version``, ``_validate_project_exists``), show interactive prompts
(``get_interactive_bump_type``, ``_show_interactive_preview``), and log the outcome
(``_log_bump_success``).

All symbols defined here are re-exported by ``bump.py`` so the public import
surface is unchanged.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

import questionary as qs
import semver
import typer
from loguru import logger

from rhiza_tools import console
from rhiza_tools.commands._shared import (
    COOL_STYLE,
    NON_INTERACTIVE_ERRORS,
)
from rhiza_tools.commands.bump_engine import _get_files_to_modify
from rhiza_tools.commands.bump_versioning import (
    _denormalize_pep440_to_semver,
    get_next_prerelease,
)


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
        try:
            with open("pyproject.toml", "rb") as f:
                data = tomllib.load(f)
            # Convert PEP 440 format back to semver format for compatibility
            # e.g., 0.1.1a1 -> 0.1.1-alpha.1
            return _denormalize_pep440_to_semver(str(data["project"]["version"]))
        except (OSError, tomllib.TOMLDecodeError, KeyError) as e:
            console.error(f"Failed to read version from pyproject.toml: {e}")
            raise typer.Exit(code=1) from None
    elif language == Language.GO:
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
    else:
        console.error(f"Unsupported language: {language}")
        raise typer.Exit(code=1)


def get_interactive_bump_type(current_version_str: str) -> str:
    """Get bump type from user through interactive prompt.

    Displays an interactive menu with all available bump types and their
    resulting versions. Returns the selected new version string.

    Args:
        current_version_str: The current version string (semver-compatible).

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
    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        console.error(f"Invalid semantic version in configuration: {current_version_str}")
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

    try:
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
            style=COOL_STYLE,
        ).ask()
    except NON_INTERACTIVE_ERRORS:
        console.error("Interactive selection not available in non-interactive environment")
        raise typer.Exit(code=1) from None

    if not choice:
        raise typer.Exit(code=0)

    # Extract the new version string from the choice. Each menu label has the
    # form Label (Current -> New); the portion after the arrow is what we keep.
    # Check if the choice contains the expected format (skip separators)
    if "-> " not in choice:
        console.error("Invalid choice selection")
        raise typer.Exit(code=1)

    new_version: str = choice.split("-> ")[1].rstrip(")")
    return new_version


def _validate_project_exists(language: Language) -> None:
    """Validate that required project files exist for the specified language.

    Args:
        language: The programming language (python or go).

    Raises:
        typer.Exit: If required project files are not found.
    """
    if language == Language.PYTHON:
        if not Path("pyproject.toml").exists():
            console.error("Python project detected but pyproject.toml not found.")
            console.error("Please create a pyproject.toml file with the current version.")
            raise typer.Exit(code=1)
    elif language == Language.GO:
        if not Path("go.mod").exists():
            console.error("Go language specified but go.mod not found.")
            console.error("Please create a go.mod file for your Go project.")
            raise typer.Exit(code=1)
        if not Path("VERSION").exists():
            console.error("Go project detected but VERSION file not found.")
            console.error("Please create a VERSION file with the current version.")
            raise typer.Exit(code=1)
    else:
        console.error(f"Unsupported language: {language}")
        raise typer.Exit(code=1)


def _log_bump_success(current_version_str: str, config: Any, language: Language) -> None:
    """Log successful version bump and post-bump instructions.

    Args:
        current_version_str: The original version string before the bump.
        config: The bumpversion configuration object.
        language: The programming language (python or go).
    """
    updated_version = get_current_version(language)
    success_msg = (
        f"\n{typer.style('✓', fg=typer.colors.GREEN, bold=True)} "
        f"Version bumped: {current_version_str} -> {updated_version}"
    )
    console.success(success_msg)

    # Show which files were actually modified
    files = _get_files_to_modify(config)
    if files:
        console.info(f"\n{typer.style('Modified files:', fg=typer.colors.CYAN, bold=True)}")
        for file_path in files:
            if file_path.exists():
                console.info(f"  • {file_path}")
    else:
        # Show common files that typically get modified
        console.info(f"\n{typer.style('Modified files:', fg=typer.colors.CYAN, bold=True)}")
        for file_path in [Path("pyproject.toml"), Path("VERSION"), Path("setup.py"), Path("setup.cfg")]:
            if file_path.exists():
                # Check if file was actually modified by checking content
                try:
                    content = file_path.read_text()
                    if updated_version in content:
                        console.info(f"  • {file_path}")
                except Exception:  # nosec B110 - safe to ignore file read errors  # noqa: S110, BLE001
                    pass

    console.info("\nDon't forget to run 'uv lock' to update the lockfile if needed.")


def _show_interactive_preview(
    current_version_str: str,
    new_version_str: str,
    current_git_branch: str,
) -> tuple[bool, bool, bool]:
    """Show interactive preview and prompt for commit/push decisions.

    In interactive mode, the user is asked step-by-step whether to proceed
    with the bump, whether to commit the changes, and whether to push.

    Args:
        current_version_str: Current version.
        new_version_str: New version.
        current_git_branch: Current git branch.

    Returns:
        Tuple of (proceed, commit, push). ``proceed`` is False if the user
        cancels the bump entirely.
    """
    # Show preview
    console.info("\nPreview of changes:")
    console.info(f"  Version: {current_version_str} → {new_version_str}")
    console.info(f"  Branch: {current_git_branch}")

    # Confirm bump
    try:
        proceed = cast(bool, qs.confirm("Proceed with version bump?", default=True, style=COOL_STYLE).ask())
    except NON_INTERACTIVE_ERRORS:
        logger.debug("Running in non-interactive environment, proceeding automatically")
        proceed = True

    if not proceed:
        return False, False, False

    # Ask about commit
    try:
        commit = cast(bool, qs.confirm("Commit the changes?", default=True, style=COOL_STYLE).ask())
    except NON_INTERACTIVE_ERRORS:
        logger.debug("Running in non-interactive environment, committing automatically")
        commit = True

    # Ask about push (only if committing)
    push = False
    if commit:
        try:
            push = cast(bool, qs.confirm("Push changes to remote?", default=False, style=COOL_STYLE).ask())
        except NON_INTERACTIVE_ERRORS:
            logger.debug("Running in non-interactive environment, skipping push")
            push = False

    return True, commit, push
