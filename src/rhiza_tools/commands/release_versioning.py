"""Bump-type resolution for the release command.

The release command can optionally bump the version before tagging. Working out
*which* version to bump to — from an explicit ``--bump`` type, the ``--with-bump``
flag, or an interactive prompt — is a self-contained concern with no git
plumbing, so it lives here rather than in ``release.py``. ``release.py``
re-exports these helpers, so the public import surface is unchanged.
"""

from pathlib import Path

import semver
import typer
from loguru import logger

from rhiza_tools import console
from rhiza_tools.commands._shared import NON_INTERACTIVE_ERRORS
from rhiza_tools.commands.bump import (
    BumpOptions,
    Language,
    _resolve_bump_baseline,
    bump_command,
    get_bumped_version_from_type,
    get_current_version,
    get_interactive_bump_type,
)

# Combined tuple for catching both typer.Exit and non-interactive environment errors.
_EXIT_OR_NON_INTERACTIVE: tuple[type[BaseException], ...] = (typer.Exit, *NON_INTERACTIVE_ERRORS)


def _get_bump_type_interactively(
    non_interactive: bool, bump_type: str | None, dry_run: bool, with_bump: bool = False, *, language: Language
) -> tuple[bool, str | None]:
    """Get bump version interactively or from parameters.

    Uses the same interactive selection as the bump command to ensure consistent
    behavior between ``rhiza-tools bump`` and ``rhiza-tools release --with-bump``.

    Args:
        non_interactive: If True, skip interactive prompts.
        bump_type: Explicit bump type provided (e.g., "MAJOR", "MINOR", "PATCH").
        dry_run: If True, the bump will be simulated (handled by caller).
        with_bump: If True, enable interactive bump selection directly.
        language: The programming language for version reading.

    Returns:
        Tuple of (should_bump, new_version_string). The version string is the
        explicit new version (not a bump type keyword).
    """
    if bump_type:
        return _resolve_explicit_bump_type(bump_type, language)

    if with_bump:
        return _resolve_with_bump_flag(non_interactive, language)

    if not non_interactive:
        return _resolve_interactive_prompt(language)

    # Non-interactive without --with-bump or --bump: no bump
    return False, None


def _resolve_explicit_bump_type(bump_type: str, language: Language) -> tuple[bool, str | None]:
    """Resolve version from an explicitly provided bump type.

    Args:
        bump_type: The bump type keyword (e.g., "MAJOR", "MINOR", "PATCH").
        language: The programming language for version reading.

    Returns:
        Tuple of (True, new_version_string).

    Raises:
        typer.Exit: If the current version is invalid or the bump type is unsupported.
    """
    current_version_str = _resolve_bump_baseline(get_current_version(language))
    try:
        current_semver = semver.Version.parse(current_version_str)
    except ValueError:
        console.error(f"Invalid semantic version: {current_version_str}")
        raise typer.Exit(code=1) from None
    new_version = get_bumped_version_from_type(current_semver, bump_type.lower())
    if not new_version:
        console.error(f"Invalid bump type: {bump_type}")
        raise typer.Exit(code=1)
    return True, new_version


def _resolve_with_bump_flag(non_interactive: bool, language: Language) -> tuple[bool, str | None]:
    """Resolve version when --with-bump flag is set.

    In non-interactive mode defaults to patch; otherwise prompts interactively.

    Args:
        non_interactive: If True, default to a patch bump.
        language: The programming language for version reading.

    Returns:
        Tuple of (should_bump, new_version_string).
    """
    if non_interactive:
        console.warning("--with-bump in non-interactive mode without --bump type, defaulting to patch")
        current_version_str = _resolve_bump_baseline(get_current_version(language))
        current_semver = semver.Version.parse(current_version_str)
        return True, str(current_semver.bump_patch())

    current_version_str = _resolve_bump_baseline(get_current_version(language))
    try:
        new_version = get_interactive_bump_type(current_version_str)
    except _EXIT_OR_NON_INTERACTIVE:
        return False, None
    return True, new_version


def _resolve_interactive_prompt(language: Language) -> tuple[bool, str | None]:
    """Prompt the user interactively whether to bump before releasing.

    Args:
        language: The programming language for version reading.

    Returns:
        Tuple of (should_bump, new_version_string).
    """
    import questionary as qs

    try:
        should_bump = qs.confirm(
            "Would you like to bump the version before releasing?",
            default=False,
        ).ask()
    except NON_INTERACTIVE_ERRORS:
        logger.debug("Running in non-interactive environment")
        return False, None

    if not should_bump:
        return False, None

    current_version_str = _resolve_bump_baseline(get_current_version(language))
    try:
        new_version = get_interactive_bump_type(current_version_str)
    except _EXIT_OR_NON_INTERACTIVE:
        return False, None
    return True, new_version


def _perform_version_bump(new_version: str, dry_run: bool, language: Language, config: Path | None = None) -> str:
    """Perform version bump with validation.

    Args:
        new_version: The explicit new version string to bump to.
        dry_run: If True, only simulate the bump.
        language: The programming language for the bump.
        config: Optional path to the .cfg.toml bumpversion config file.

    Returns:
        The new version string.

    Raises:
        typer.Exit: If the bump operation fails.
    """
    console.info(f"Bumping version to: {new_version}")

    bump_command(
        BumpOptions(
            version=new_version,
            dry_run=dry_run,
            commit=True,
            push=False,  # Don't push yet, we'll do it after tagging
            allow_dirty=False,
            language=language,
            config=config,
        )
    )

    if dry_run:
        console.info("[DRY-RUN] Version would be bumped before release")

    return new_version
