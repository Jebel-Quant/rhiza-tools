"""Interactive prompts for the bump command.

This module holds the ``questionary``-backed interactive helpers: choosing a bump
type from a menu (``get_interactive_bump_type``) and confirming the
proceed/commit/push decisions (``_show_interactive_preview``). Keeping every
``questionary`` call in one module means tests only ever patch ``qs`` at this
single path.

All public symbols defined here are re-exported by ``bump/__init__.py`` so the
public import surface is unchanged.
"""

from __future__ import annotations

from typing import cast

import questionary as qs
import typer
from loguru import logger

from rhiza_tools import console
from rhiza_tools.commands._project import (
    parse_semver_or_exit,
)
from rhiza_tools.commands._prompts import (
    COOL_STYLE,
    NON_INTERACTIVE_ERRORS,
)
from rhiza_tools.commands.bump.versioning import (
    get_next_prerelease,
)


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
    current_version = parse_semver_or_exit(current_version_str)

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


def _confirm(question: str, *, default: bool, non_interactive_default: bool, non_interactive_log: str) -> bool:
    """Ask a yes/no question, falling back to a default in non-interactive envs.

    Args:
        question: The prompt text shown to the user.
        default: The default answer highlighted in the interactive prompt.
        non_interactive_default: The value to return when no TTY is available.
        non_interactive_log: Debug message logged when the fallback is taken.

    Returns:
        The user's answer, or ``non_interactive_default`` outside a TTY.
    """
    try:
        return cast(bool, qs.confirm(question, default=default, style=COOL_STYLE).ask())
    except NON_INTERACTIVE_ERRORS:
        logger.debug(non_interactive_log)
        return non_interactive_default


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
    console.info("\nPreview of changes:")
    console.info(f"  Version: {current_version_str} → {new_version_str}")
    console.info(f"  Branch: {current_git_branch}")

    proceed = _confirm(
        "Proceed with version bump?",
        default=True,
        non_interactive_default=True,
        non_interactive_log="Running in non-interactive environment, proceeding automatically",
    )
    if not proceed:
        return False, False, False

    commit = _confirm(
        "Commit the changes?",
        default=True,
        non_interactive_default=True,
        non_interactive_log="Running in non-interactive environment, committing automatically",
    )

    # Ask about push (only if committing)
    push = False
    if commit:
        push = _confirm(
            "Push changes to remote?",
            default=False,
            non_interactive_default=False,
            non_interactive_log="Running in non-interactive environment, skipping push",
        )

    return True, commit, push
