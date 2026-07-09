"""Bump-type resolution for the release command.

A release always bumps the version before tagging. Working out *which* version
to bump to — from an explicit ``--bump`` type, an interactive prompt, or a patch
default in non-interactive mode — is a self-contained concern with no git
plumbing, so it lives here rather than in ``release.py``. ``release.py``
re-exports these helpers, so the public import surface is unchanged.
"""

from pathlib import Path

import typer

from rhiza_tools import console
from rhiza_tools.commands._project import parse_semver_or_exit
from rhiza_tools.commands.bump import (
    BumpOptions,
    Language,
    _resolve_bump_baseline,
    bump_command,
    get_bumped_version_from_type,
    get_current_version,
    get_interactive_bump_type,
)


def _resolve_required_bump(non_interactive: bool, bump_type: str | None, *, language: Language) -> tuple[bool, str]:
    """Resolve the version bump to apply before releasing.

    A release always bumps, so this never returns "no bump". The bump target is
    resolved, in order of precedence, from: an explicit ``bump_type``; a patch
    default when running non-interactively without one; or an interactive prompt
    for the bump type. Cancelling the interactive prompt raises ``typer.Exit``
    (via :func:`get_interactive_bump_type`), aborting the release.

    The leading boolean in the return tuple is intentionally always ``True`` to
    preserve a stable ``(required, new_version)`` shape for callers. In the
    release flow, ``required`` is unconditional because a release always requires
    a version bump.

    Args:
        non_interactive: If True, skip prompts and default to a patch bump.
        bump_type: Explicit bump type (e.g., "MAJOR", "MINOR", "PATCH"), if given.
        language: The programming language for version reading.

    Returns:
        Tuple of ``(True, new_version_string)`` where the boolean is a fixed
        compatibility flag and ``new_version_string`` is the explicit version to
        bump to (not a bump-type keyword).
    """
    if bump_type:
        return True, _resolve_explicit_bump_type(bump_type, language)

    current_version_str = _resolve_bump_baseline(get_current_version(language))

    if non_interactive:
        console.warning("No --bump type given in non-interactive mode, defaulting to patch")
        current_semver = parse_semver_or_exit(current_version_str)
        return True, str(current_semver.bump_patch())

    return True, get_interactive_bump_type(current_version_str)


def _resolve_explicit_bump_type(bump_type: str, language: Language) -> str:
    """Resolve version from an explicitly provided bump type.

    Args:
        bump_type: The bump type keyword (e.g., "MAJOR", "MINOR", "PATCH").
        language: The programming language for version reading.

    Returns:
        The new version string.

    Raises:
        typer.Exit: If the current version is invalid or the bump type is unsupported.
    """
    current_version_str = _resolve_bump_baseline(get_current_version(language))
    current_semver = parse_semver_or_exit(current_version_str)
    new_version = get_bumped_version_from_type(current_semver, bump_type.lower())
    if not new_version:
        console.error(f"Invalid bump type: {bump_type}. Valid bump types (case-insensitive) are: major, minor, patch.")
        raise typer.Exit(code=1)
    return new_version


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
    if dry_run:
        console.info(f"[DRY-RUN] Would bump version to: {new_version}")
    else:
        console.info(f"Bumping version to: {new_version}")

    bump_command(
        BumpOptions(
            version=new_version,
            dry_run=dry_run,
            commit=True,
            push=False,  # Do not push yet; we will do it after tagging
            allow_dirty=False,
            language=language,
            config=config,
        )
    )

    if dry_run:
        console.info("[DRY-RUN] Version would be bumped before release")

    return new_version
