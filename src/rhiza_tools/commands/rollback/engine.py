"""Execution engine for the rollback command.

These helpers perform the state-mutating steps of a rollback — deleting the
remote and local tags, resolving and reverting the bump commit, and pushing the
revert — plus the orchestration that sequences them. They delegate the actual
git plumbing to ``rollback/git.py`` and the revert push to ``rollback/io.py``;
they contain no interactive prompts of their own.

All symbols defined here are re-exported by ``rollback.py`` so the public import
surface is unchanged.
"""

from __future__ import annotations

import typer

from rhiza_tools import console
from rhiza_tools.commands.rollback.git import (
    _delete_local_tag,
    _delete_remote_tag,
    _get_tag_commit,
    _revert_bump_commit,
)
from rhiza_tools.commands.rollback.io import _push_revert


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


def _resolve_revert_commit(
    tag: str,
    revert_bump: bool,
    is_bump: bool,
    exists_locally: bool,
) -> tuple[str | None, bool]:
    """Resolve the commit to revert, before any tags are deleted.

    Args:
        tag: The tag to rollback.
        revert_bump: Whether a bump revert was requested.
        is_bump: Whether the tagged commit is a bump commit.
        exists_locally: Whether the tag exists locally.

    Returns:
        Tuple of (tag_commit, revert_bump). ``tag_commit`` is the resolved commit
        hash, or None when a revert is not applicable or the commit can't be
        found; ``revert_bump`` is disabled when the commit can't be found.
    """
    if not (revert_bump and is_bump and exists_locally):
        return None, revert_bump

    tag_commit = _get_tag_commit(tag)
    if not tag_commit:
        console.error(f"Could not find commit for tag: {tag}")
        console.error("Skipping bump revert but proceeding with tag deletion.")
        return None, False

    return tag_commit, revert_bump


def _revert_and_push(tag_commit: str, dry_run: bool, non_interactive: bool) -> bool:
    """Revert the bump commit and push the revert.

    Args:
        tag_commit: The commit hash to revert.
        dry_run: If True, only simulate changes.
        non_interactive: If True, skip confirmation prompts.

    Returns:
        True if both the revert and its push succeeded.
    """
    if not _revert_bump_commit(tag_commit, dry_run):
        if not dry_run:
            console.warning("Bump revert failed. Tags were still deleted.")
            console.warning("You may need to manually revert the bump commit.")
        return False

    return _push_revert(dry_run, non_interactive)


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
    tag_commit, revert_bump = _resolve_revert_commit(tag, revert_bump, is_bump, exists_locally)

    success = _delete_rollback_tags(tag, exists_locally, exists_remotely, dry_run)

    # Revert bump commit and push (if requested)
    if revert_bump and is_bump and tag_commit and not _revert_and_push(tag_commit, dry_run, non_interactive):
        success = False

    return success
