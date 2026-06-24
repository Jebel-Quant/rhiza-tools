"""Command to push release tags to remote.

This module implements release functionality that validates the git repository
state and pushes tags to remote, triggering the release workflow. Tags are
created by bump-my-version during the bump process.

Supports Python projects (pyproject.toml) and Go projects (go.mod + VERSION file).
The project language is auto-detected when not explicitly specified.

Example:
    Push a release tag::

        from rhiza_tools.commands.release import release_command
        release_command()

    Dry run to preview release::

        release_command(dry_run=True)

    Release a Go project::

        release_command(language=Language.GO)
"""

from pathlib import Path

import semver
import typer

from rhiza_tools import console
from rhiza_tools.commands._shared import (
    get_latest_remote_version,
)
from rhiza_tools.commands._shared import (
    run_git_command as run_git_command,
)
from rhiza_tools.commands.bump import (
    Language,
    _validate_project_exists,
    get_current_version,
)

# Git plumbing (tag lookup, push, branch checks) lives in release/git.py; re-exported
# here so the public import surface (and existing tests) keep working.
from rhiza_tools.commands.release.git import (
    _confirm_and_push_tag as _confirm_and_push_tag,
)
from rhiza_tools.commands.release.git import (
    _show_commits_since_last_tag as _show_commits_since_last_tag,
)
from rhiza_tools.commands.release.git import (
    _validate_tag_state as _validate_tag_state,
)
from rhiza_tools.commands.release.git import (
    check_branch_status as check_branch_status,
)
from rhiza_tools.commands.release.git import (
    check_clean_working_tree as check_clean_working_tree,
)
from rhiza_tools.commands.release.git import (
    check_tag_exists as check_tag_exists,
)
from rhiza_tools.commands.release.git import (
    get_current_branch as get_current_branch,
)
from rhiza_tools.commands.release.git import (
    get_default_branch as get_default_branch,
)
from rhiza_tools.commands.release.git import (
    push_tag as push_tag,
)

# Bump-type resolution lives in release/versioning.py; re-exported here so the
# public import surface (and existing tests) keep using ``release.<helper>``.
from rhiza_tools.commands.release.versioning import (
    _perform_version_bump,
    _resolve_required_bump,
)
from rhiza_tools.commands.release.versioning import (
    _resolve_explicit_bump_type as _resolve_explicit_bump_type,
)


def _get_release_version(dry_run: bool, bumped_new_version: str | None, language: Language) -> tuple[str, str]:
    """Get current version and tag for release.

    Args:
        dry_run: If True and version was bumped, use bumped version.
        bumped_new_version: New version if bump was performed.
        language: The programming language for version reading.

    Returns:
        Tuple of (current_version, tag).
    """
    current_version = bumped_new_version if dry_run and bumped_new_version else get_current_version(language)

    tag = f"v{current_version}"
    console.info(f"Current version: {current_version}")
    console.info(f"Expected tag: {tag}")

    return current_version, tag


def _check_repository_state(dry_run: bool, current_branch: str, default_branch: str) -> None:
    """Check repository state before release.

    Args:
        dry_run: If True, skip some checks.
        current_branch: Current git branch.
        default_branch: Default git branch.
    """
    # Note if not on default branch
    if current_branch != default_branch:
        console.info(f"Note: You are on branch '{current_branch}' (default branch is '{default_branch}')")

    # Check for uncommitted changes (skip in dry-run mode)
    if not dry_run:
        check_clean_working_tree()
        check_branch_status(current_branch)


def _handle_tag_validation(dry_run: bool, bumped_new_version: str | None, tag: str, current_version: str) -> None:
    """Validate tag state before release.

    Args:
        dry_run: If True and version was bumped, use relaxed validation.
        bumped_new_version: New version if bump was performed.
        tag: Tag name to validate.
        current_version: Current version string.

    Raises:
        typer.Exit: If tag validation fails.
    """
    if dry_run and bumped_new_version:
        # In dry-run with bump, the tag won't exist yet - just check it's not already on remote
        _, exists_remotely = check_tag_exists(tag)
        if exists_remotely:
            console.error(f"Tag '{tag}' already exists on remote")
            console.error(f"The release for version {current_version} has already been published.")
            console.error("If this was unintentional, you can delete the remote tag and retry:")
            console.error(f"  git push origin :refs/tags/{tag}")
            raise typer.Exit(code=1)
        console.info(f"[DRY-RUN] Tag '{tag}' would be created by the bump and release process")
    else:
        _validate_tag_state(tag, current_version)


def _check_release_version_monotonic(version_str: str, allow_older: bool) -> None:
    """Ensure the version being released is newer than the latest remote release.

    This is the authoritative guard against issue #1126: it refuses to push a
    tag whose version is not strictly greater than the highest version already
    published on the remote, regardless of what the (possibly stale) local
    ``pyproject.toml`` says.

    When the remote has no published version tags (first release) or cannot be
    reached, the check is skipped so normal first releases and offline dry-runs
    still work.

    Args:
        version_str: The version that is about to be released (with or without a
            leading ``v``).
        allow_older: If True, downgrade the hard error to a warning so that
            intentional maintenance / back-branch releases can proceed.

    Raises:
        typer.Exit: If the version is not newer than the latest remote release
            and ``allow_older`` is False.
    """
    latest_remote = get_latest_remote_version()
    if latest_remote is None:
        return

    try:
        candidate = semver.Version.parse(version_str[1:] if version_str.startswith("v") else version_str)
    except ValueError:
        console.error(f"Invalid semantic version: {version_str}")
        raise typer.Exit(code=1) from None

    if candidate > latest_remote:
        console.success(f"Preflight: v{candidate} is newer than the latest remote release v{latest_remote}")
        return

    relation = "the same as" if candidate == latest_remote else "older than"
    if allow_older:
        console.warning(
            f"Version v{candidate} is {relation} the latest remote release v{latest_remote}; "
            "proceeding because --allow-older was set."
        )
        return

    console.error(f"Refusing to release v{candidate}: it is {relation} the latest remote release v{latest_remote}.")
    console.error("Your branch likely diverged before a newer release was merged (issue #1126).")
    console.error("To resolve:")
    console.error("  Sync with the latest release, e.g.:  git pull --rebase origin <default-branch>")
    console.error(f"  Then bump again so the new version is higher than v{latest_remote}.")
    console.error("For an intentional maintenance/back-branch release, re-run with --allow-older.")
    raise typer.Exit(code=1)


def release_command(
    bump_type: str | None = None,
    push: bool = False,
    dry_run: bool = False,
    non_interactive: bool = False,
    language: Language | None = None,
    config: Path | None = None,
    allow_older: bool = False,
) -> None:
    """Bump the version and push a release tag to remote.

    A release always bumps the version before tagging — there is no tag-only
    path. This command performs the following steps:
    1. Detects the project language (Python or Go) unless explicitly specified
    2. Resolves the bump (explicit ``bump_type``, interactive prompt, or a patch
       default in non-interactive mode) and bumps the version
    3. Reads the current version from pyproject.toml (Python) or VERSION file (Go)
    4. Validates the git repository state (clean working tree, up-to-date with remote)
    5. Checks that a tag exists for the current version (created by bump-my-version)
    6. Pushes the tag to remote, triggering the release workflow

    Args:
        bump_type: Optional bump type (MAJOR, MINOR, PATCH) to apply. When omitted,
            the bump type is selected interactively (or defaults to patch in
            non-interactive mode).
        push: If True, push changes without prompting.
        dry_run: If True, show what would be done without making any changes.
        non_interactive: If True, skip all confirmation prompts and default the
            bump to patch when no ``bump_type`` is given.
        language: Programming language (python or go). Auto-detected if not specified.
        config: Optional path to the .cfg.toml bumpversion config file.
        allow_older: If True, permit releasing a version that is not strictly
            greater than the latest version already published on the remote.
            Required for intentional back-branch / maintenance releases.

    Raises:
        typer.Exit: If no supported project files are found, repository is not clean,
            tag doesn't exist, or any git operations fail.

    Example:
        Bump (interactive) and release::

            release_command()

        Preview what would happen::

            release_command(dry_run=True)

        Non-interactive patch release::

            release_command(non_interactive=True)

        Explicit bump and release::

            release_command(bump_type="MINOR", push=True)

        Release a Go project::

            release_command(language=Language.GO)
    """
    # Detect or validate project language
    if language is None:
        language = Language.detect()
        if language is None:
            console.error("No supported project files found in current directory.")
            console.error("Python projects need pyproject.toml; Go projects need go.mod and VERSION.")
            raise typer.Exit(code=1)
    else:
        _validate_project_exists(language)

    # Get current branch early
    current_branch = get_current_branch()
    console.info(f"Current branch: {typer.style(current_branch, fg=typer.colors.CYAN, bold=True)}")

    # A release always bumps: resolve the bump target (explicit, interactive, or
    # patch default in non-interactive mode).
    _, new_version = _resolve_required_bump(non_interactive, bump_type, language=language)

    # ── Preflight validation: check everything BEFORE making any changes ──
    default_branch = get_default_branch()
    _check_repository_state(dry_run, current_branch, default_branch)

    # Ensure the version we are about to release is strictly newer than the
    # latest version already published on the remote (issue #1126). Runs in all
    # modes (including dry-run) and before any mutation.
    _check_release_version_monotonic(new_version, allow_older)

    # Pre-validate that the new tag won't conflict with remote
    if not dry_run:
        new_tag = f"v{new_version}"
        _, exists_remotely = check_tag_exists(new_tag)
        if exists_remotely:
            console.error(f"Tag '{new_tag}' already exists on remote")
            console.error(f"The release for version {new_version} has already been published.")
            console.error("No changes were made. To resolve:")
            console.error(f"  Delete the remote tag:  git push origin :refs/tags/{new_tag}")
            console.error("  Or choose a different version to bump to.")
            raise typer.Exit(code=1)
        console.success(f"Preflight: tag '{new_tag}' is available on remote")

    # ── Execute: all preflight checks passed, safe to make changes ──

    # Perform the bump (bump_command runs its own internal preflight)
    bumped_new_version = _perform_version_bump(new_version, dry_run, language, config)

    # Get current version and tag
    current_version, tag = _get_release_version(dry_run, bumped_new_version, language)

    # Validate tag state (for non-bump cases, ensures local tag exists)
    _handle_tag_validation(dry_run, bumped_new_version, tag, current_version)

    # Push tag
    console.info("Preparing to push tag to remote...")
    console.info(f"Pushing tag '{tag}' to origin will trigger the release workflow.")

    # Show commits since last tag (if any)
    _show_commits_since_last_tag(tag)

    # Confirm and push (bump commit + tag together)
    _confirm_and_push_tag(
        tag, push, dry_run, non_interactive, bump_branch=current_branch if bumped_new_version else None
    )

    if dry_run:
        console.info("[DRY-RUN] Release process completed (no changes made)")
    else:
        console.success("Release process completed successfully!")
