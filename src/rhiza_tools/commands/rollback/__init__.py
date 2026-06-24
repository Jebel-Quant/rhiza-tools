"""Command to rollback a release and/or version bump.

This module implements rollback functionality that safely reverses release
and bump operations. It can delete local and remote tags, revert bump commits,
and restore the project to a previous version state.

Example:
    Rollback the most recent release::

        from rhiza_tools.commands.rollback import rollback_command
        rollback_command()

    Rollback a specific tag::

        rollback_command(tag="v1.2.3")

    Dry run to preview rollback::

        rollback_command(dry_run=True)
"""

from __future__ import annotations

from dataclasses import dataclass

import questionary as qs
import typer
from loguru import logger

from rhiza_tools import console
from rhiza_tools.commands._shared import (
    COOL_STYLE,
    NON_INTERACTIVE_ERRORS,
    run_git_command,
    validate_pyproject_exists,
)
from rhiza_tools.commands.release import check_tag_exists

# Git tag/commit plumbing lives in rollback/git.py; re-exported here so callers and
# existing tests keep importing ``rollback.<helper>``.
from rhiza_tools.commands.rollback.git import (
    _delete_local_tag,
    _delete_remote_tag,
    _get_previous_version_from_tags,
    _get_tag_commit,
    _get_tag_details,
    _is_bump_commit,
    _revert_bump_commit,
)

# Interactive UI and display helpers live in rollback/io.py; re-exported here so
# callers and existing tests keep importing ``rollback.<helper>``.
from rhiza_tools.commands.rollback.io import (
    _confirm_rollback as _confirm_rollback,
)
from rhiza_tools.commands.rollback.io import (
    _push_revert as _push_revert,
)
from rhiza_tools.commands.rollback.io import (
    _select_tag_interactively as _select_tag_interactively,
)
from rhiza_tools.commands.rollback.io import (
    _show_rollback_plan as _show_rollback_plan,
)


@dataclass
class RollbackOptions:
    """Configuration options for the rollback command.

    Attributes:
        tag: The tag to rollback (e.g., "v1.2.3"). None for interactive selection.
        revert_bump: If True, also revert the version bump commit.
        dry_run: If True, show what would change without actually changing anything.
        non_interactive: If True, skip all confirmation prompts.
    """

    tag: str | None = None
    revert_bump: bool = False
    dry_run: bool = False
    non_interactive: bool = False


def _get_recent_tags(limit: int = 10) -> list[str]:
    """Get recent version tags sorted by version descending.

    Args:
        limit: Maximum number of tags to return.

    Returns:
        List of tag names (e.g., ["v1.2.3", "v1.2.2", ...]).
    """
    result = run_git_command(
        ["git", "tag", "--sort=-version:refname", "-l", "v*"],
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []

    tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]
    return tags[:limit]


def _validate_rollback_preconditions(tag: str) -> tuple[bool, bool]:
    """Validate that the tag exists somewhere before attempting rollback.

    Args:
        tag: The tag to validate.

    Returns:
        Tuple of (exists_locally, exists_remotely).

    Raises:
        typer.Exit: If the tag doesn't exist anywhere.
    """
    exists_locally, exists_remotely = check_tag_exists(tag)

    if not exists_locally and not exists_remotely:
        console.error(f"Tag '{tag}' does not exist locally or on remote.")
        console.error("Nothing to rollback.")
        raise typer.Exit(code=1)

    return exists_locally, exists_remotely


def _resolve_tag(options: RollbackOptions) -> str:
    """Determine which tag to rollback from options or interactively.

    Args:
        options: Rollback configuration options.

    Returns:
        The resolved tag name with 'v' prefix.

    Raises:
        typer.Exit: If no tags are found in non-interactive mode.
    """
    tag = options.tag
    if not tag:
        if options.non_interactive:
            recent_tags = _get_recent_tags(limit=1)
            if not recent_tags:
                console.error("No version tags found in the repository.")
                raise typer.Exit(code=1)
            tag = recent_tags[0]
            console.info(f"Non-interactive mode: rolling back most recent tag: {tag}")
        else:
            recent_tags = _get_recent_tags()
            tag = _select_tag_interactively(recent_tags)

    if not tag.startswith("v"):
        tag = f"v{tag}"

    return tag


def _should_revert_bump(options: RollbackOptions, exists_locally: bool, is_bump: bool) -> bool:
    """Determine whether the bump commit should be reverted.

    If ``--revert-bump`` was passed, returns True immediately. Otherwise,
    prompts the user interactively when the tagged commit looks like a bump.

    Args:
        options: Rollback configuration options.
        exists_locally: Whether the tag exists locally.
        is_bump: Whether the tagged commit is a bump commit.

    Returns:
        True if the bump commit should be reverted.
    """
    if options.revert_bump:
        return True

    if options.non_interactive or options.dry_run or not exists_locally or not is_bump:
        return False

    try:
        return bool(
            qs.confirm(
                "The tagged commit appears to be a version bump. Revert it too?",
                default=True,
                style=COOL_STYLE,
            ).ask()
        )
    except NON_INTERACTIVE_ERRORS:
        logger.debug("Running in non-interactive environment")
        return False


def _delete_rollback_tags(
    tag: str,
    exists_locally: bool,
    exists_remotely: bool,
    dry_run: bool,
) -> bool:
    """Delete the remote then local tag for a rollback.

    The remote tag is deleted first to stop any in-progress release. A failure
    to delete the remote tag aborts the rollback in non-dry-run mode.

    Args:
        tag: The tag to delete.
        exists_locally: Whether the tag exists locally.
        exists_remotely: Whether the tag exists on remote.
        dry_run: If True, only simulate changes.

    Returns:
        True if all attempted deletions succeeded.

    Raises:
        typer.Exit: If the remote tag deletion fails (non-dry-run).
    """
    success = True

    # Delete remote tag first to stop any in-progress release
    if exists_remotely and not _delete_remote_tag(tag, dry_run):
        success = False
        if not dry_run:
            console.error("Failed to delete remote tag. Aborting remaining steps.")
            console.error("You can retry or manually delete with:")
            console.error(f"  git push origin :refs/tags/{tag}")
            raise typer.Exit(code=1)

    # Delete local tag
    if exists_locally and not _delete_local_tag(tag, dry_run):
        success = False
        if not dry_run:
            console.warning(f"Failed to delete local tag. Delete manually: git tag -d {tag}")

    return success


def _execute_rollback(
    tag: str,
    exists_locally: bool,
    exists_remotely: bool,
    revert_bump: bool,
    is_bump: bool,
    dry_run: bool,
    non_interactive: bool,
) -> bool:
    """Execute the rollback steps: delete tags, revert bump, push.

    Args:
        tag: The tag to rollback.
        exists_locally: Whether the tag exists locally.
        exists_remotely: Whether the tag exists on remote.
        revert_bump: Whether to revert the bump commit.
        is_bump: Whether the tagged commit is a bump commit.
        dry_run: If True, only simulate changes.
        non_interactive: If True, skip confirmation prompts.

    Returns:
        True if all steps succeeded.

    Raises:
        typer.Exit: If the remote tag deletion fails (non-dry-run).
    """
    # Get commit hash BEFORE deleting tags (needed for revert)
    tag_commit = None
    if revert_bump and is_bump and exists_locally:
        tag_commit = _get_tag_commit(tag)
        if not tag_commit:
            console.error(f"Could not find commit for tag: {tag}")
            console.error("Skipping bump revert but proceeding with tag deletion.")
            revert_bump = False

    success = _delete_rollback_tags(tag, exists_locally, exists_remotely, dry_run)

    # Revert bump commit and push (if requested)
    if revert_bump and is_bump and tag_commit:
        if not _revert_bump_commit(tag_commit, dry_run):
            success = False
            if not dry_run:
                console.warning("Bump revert failed. Tags were still deleted.")
                console.warning("You may need to manually revert the bump commit.")
        elif not _push_revert(dry_run, non_interactive):
            success = False

    return success


def _print_rollback_summary(dry_run: bool, success: bool, previous_tag: str | None) -> None:
    """Print a summary after rollback execution.

    Args:
        dry_run: Whether this was a dry run.
        success: Whether all rollback steps succeeded.
        previous_tag: The previous version tag, if any.
    """
    if dry_run:
        console.info("\n[DRY-RUN] Rollback preview complete (no changes made)")
        return

    if not success:
        console.warning("\nRollback completed with warnings. Review the output above.")
        return

    success_msg = typer.style("✓", fg=typer.colors.GREEN, bold=True)
    console.success(f"\n{success_msg} Rollback completed successfully!")

    if previous_tag:
        console.info(f"Previous version was: {previous_tag}")
        console.info("To re-release at the previous version, run:")
        console.info("  rhiza-tools release")
        console.info("To bump to a new version instead:")
        console.info("  rhiza-tools bump")
    else:
        console.info("No previous version tag found.")
        console.info("To set a new version:")
        console.info("  rhiza-tools bump <version>")


def rollback_command(options: RollbackOptions) -> None:
    """Rollback a release and/or version bump.

    This command safely reverses release and bump operations by:

    1. Deleting the release tag from remote (stops/prevents the release workflow)
    2. Deleting the release tag locally
    3. Optionally reverting the version bump commit (with ``--revert-bump``)
    4. Optionally pushing the revert commit to remote

    The command uses ``git revert`` rather than ``git reset`` to create a new
    revert commit, making it safe even when changes have been pushed to remote.

    Args:
        options: Configuration options for the rollback.

    Raises:
        typer.Exit: If the tag doesn't exist, pyproject.toml is missing,
            or any git operations fail.

    Example:
        Rollback the most recent release::

            rollback_command(RollbackOptions())

        Preview rollback::

            rollback_command(RollbackOptions(dry_run=True))

        Rollback a specific tag with bump revert::

            rollback_command(RollbackOptions(tag="v1.2.3", revert_bump=True))

        Non-interactive rollback::

            rollback_command(RollbackOptions(
                tag="v1.2.3",
                revert_bump=True,
                non_interactive=True,
            ))
    """
    validate_pyproject_exists()

    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    current_branch = result.stdout.strip()
    console.info(f"Current branch: {typer.style(current_branch, fg=typer.colors.CYAN, bold=True)}")

    tag = _resolve_tag(options)
    exists_locally, exists_remotely = _validate_rollback_preconditions(tag)

    tag_details = _get_tag_details(tag) if exists_locally else {}
    is_bump = _is_bump_commit(tag) if exists_locally else False
    previous_tag = _get_previous_version_from_tags(tag)
    revert_bump = _should_revert_bump(options, exists_locally, is_bump)

    _show_rollback_plan(tag, exists_locally, exists_remotely, revert_bump, is_bump, previous_tag, tag_details)

    if not options.dry_run and not _confirm_rollback(options.non_interactive):
        console.info("Rollback cancelled by user.")
        raise typer.Exit(code=0)

    success = _execute_rollback(
        tag, exists_locally, exists_remotely, revert_bump, is_bump, options.dry_run, options.non_interactive
    )
    _print_rollback_summary(options.dry_run, success, previous_tag)
