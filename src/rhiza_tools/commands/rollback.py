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
from pathlib import Path

import questionary as qs
import typer
from loguru import logger

from rhiza_tools import console
from rhiza_tools.commands.release import check_tag_exists, run_git_command

_COOL_STYLE = qs.Style(
    [
        ("separator", "fg:#cc5454"),
        ("qmark", "fg:#2FA4A9 bold"),
        ("question", ""),
        ("selected", "fg:#2FA4A9 bold"),
        ("pointer", "fg:#2FA4A9 bold"),
        ("highlighted", "fg:#2FA4A9 bold"),
        ("answer", "fg:#2FA4A9 bold"),
        ("text", "fg:#ffffff"),
        ("disabled", "fg:#858585 italic"),
    ]
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


def _select_tag_interactively(tags: list[str]) -> str:
    """Prompt the user to select a tag to rollback.

    Args:
        tags: List of available tags.

    Returns:
        The selected tag name.

    Raises:
        typer.Exit: If user cancels selection or no tags are available.
    """
    if not tags:
        console.error("No version tags found in the repository.")
        console.error("Nothing to rollback.")
        raise typer.Exit(code=1)

    # Annotate tags with local/remote info
    choices: list[str] = []
    for tag in tags:
        exists_locally, exists_remotely = check_tag_exists(tag)
        markers = []
        if exists_locally:
            markers.append("local")
        if exists_remotely:
            markers.append("remote")
        status = ", ".join(markers) if markers else "missing"
        choices.append(f"{tag} ({status})")

    try:
        choice = qs.select(
            "Select tag to rollback:",
            choices=choices,
            style=_COOL_STYLE,
        ).ask()
    except EOFError:
        logger.debug("Running in non-interactive environment")
        raise typer.Exit(code=1) from None

    if not choice:
        console.info("Rollback cancelled by user.")
        raise typer.Exit(code=0)

    # Extract tag name from choice string "v1.2.3 (local, remote)"
    return str(choice).split(" (")[0]


def _get_tag_commit(tag: str) -> str | None:
    """Get the commit hash that a tag points to.

    Args:
        tag: The tag name.

    Returns:
        The commit hash, or None if the tag doesn't exist locally.
    """
    result = run_git_command(["git", "rev-list", "-n", "1", tag], check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _get_tag_details(tag: str) -> dict[str, str]:
    """Get details about a tag.

    Args:
        tag: The tag name.

    Returns:
        Dictionary with commit hash, date, and message.
    """
    details: dict[str, str] = {}
    result = run_git_command(
        ["git", "show", "-s", "--format=%H|%ci|%s", tag],
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        parts = result.stdout.strip().split("|")
        if len(parts) == 3:
            details["hash"] = parts[0]
            details["date"] = parts[1]
            details["message"] = parts[2]
    return details


def _is_bump_commit(tag: str) -> bool:
    """Check if the commit the tag points to looks like a bump commit.

    Bump commits typically have messages like "Bump version: X.Y.Z → A.B.C"
    or contain version-related keywords.

    Args:
        tag: The tag name.

    Returns:
        True if the tag's commit appears to be a bump commit.
    """
    result = run_git_command(
        ["git", "log", "-1", "--format=%s", tag],
        check=False,
    )
    if result.returncode != 0:
        return False

    message = result.stdout.strip().lower()
    bump_keywords = ["bump version", "bump:", "version bump", "release version", "chore: bump"]
    return any(keyword in message for keyword in bump_keywords)


def _get_previous_version_from_tags(current_tag: str) -> str | None:
    """Find the previous version tag before the given tag.

    Args:
        current_tag: The current tag being rolled back.

    Returns:
        The previous tag name, or None if no previous tag exists.
    """
    result = run_git_command(
        ["git", "tag", "--sort=-version:refname", "-l", "v*"],
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None

    tags = [t.strip() for t in result.stdout.strip().split("\n") if t.strip()]

    try:
        idx = tags.index(current_tag)
        if idx + 1 < len(tags):
            return tags[idx + 1]
    except ValueError:
        pass

    return None


def _delete_local_tag(tag: str, dry_run: bool) -> bool:
    """Delete a tag from the local repository.

    Args:
        tag: The tag name to delete.
        dry_run: If True, only simulate deletion.

    Returns:
        True if deletion succeeded (or would succeed in dry-run).
    """
    if dry_run:
        console.info(f"[DRY-RUN] Would delete local tag: {tag}")
        return True

    result = run_git_command(["git", "tag", "-d", tag], check=False)
    if result.returncode == 0:
        console.success(f"Deleted local tag: {tag}")
        return True
    else:
        console.error(f"Failed to delete local tag: {tag}")
        console.error(f"Error: {result.stderr}")
        return False


def _delete_remote_tag(tag: str, dry_run: bool) -> bool:
    """Delete a tag from the remote repository.

    Args:
        tag: The tag name to delete.
        dry_run: If True, only simulate deletion.

    Returns:
        True if deletion succeeded (or would succeed in dry-run).
    """
    if dry_run:
        console.info(f"[DRY-RUN] Would delete remote tag: {tag}")
        return True

    console.info(f"Deleting remote tag: {tag}...")
    result = run_git_command(
        ["git", "push", "origin", f":refs/tags/{tag}"],
        check=False,
    )
    if result.returncode == 0:
        console.success(f"Deleted remote tag: {tag}")
        return True
    else:
        console.error(f"Failed to delete remote tag: {tag}")
        console.error(f"Error: {result.stderr}")
        return False


def _revert_bump_commit(tag: str, dry_run: bool) -> bool:
    """Revert the version bump commit that the tag points to.

    Creates a new revert commit rather than rewriting history, making
    this safe even when the commit has been pushed to remote.

    Args:
        tag: The tag whose commit should be reverted.
        dry_run: If True, only simulate the revert.

    Returns:
        True if revert succeeded (or would succeed in dry-run).
    """
    tag_commit = _get_tag_commit(tag)
    if not tag_commit:
        console.error(f"Could not find commit for tag: {tag}")
        return False

    if dry_run:
        result = run_git_command(
            ["git", "log", "-1", "--format=%s", tag_commit],
            check=False,
        )
        commit_msg = result.stdout.strip() if result.returncode == 0 else "unknown"
        console.info(f"[DRY-RUN] Would revert commit {tag_commit[:8]}: {commit_msg}")
        return True

    console.info(f"Reverting bump commit {tag_commit[:8]}...")
    result = run_git_command(
        ["git", "revert", "--no-edit", tag_commit],
        check=False,
    )
    if result.returncode == 0:
        console.success(f"Reverted bump commit: {tag_commit[:8]}")
        return True
    else:
        console.error(f"Failed to revert commit {tag_commit[:8]}")
        console.error(f"Error: {result.stderr}")
        console.error("You may need to resolve conflicts manually:")
        console.error(f"  git revert {tag_commit[:8]}")
        return False


def _push_revert(dry_run: bool, non_interactive: bool) -> bool:
    """Push the revert commit to remote.

    Args:
        dry_run: If True, only simulate the push.
        non_interactive: If True, skip confirmation prompt.

    Returns:
        True if push succeeded (or would succeed in dry-run).
    """
    if dry_run:
        console.info("[DRY-RUN] Would push revert commit to remote")
        return True

    should_push = non_interactive
    if not non_interactive:
        try:
            should_push = qs.confirm(
                "Push revert commit to remote?",
                default=True,
                style=_COOL_STYLE,
            ).ask()
        except EOFError:
            logger.debug("Running in non-interactive environment, proceeding with push")
            should_push = True

    if not should_push:
        console.info("Revert commit created locally but not pushed.")
        console.info("Push manually when ready: git push")
        return True

    result = run_git_command(["git", "push"], check=False)
    if result.returncode == 0:
        console.success("Revert commit pushed to remote.")
        return True
    else:
        console.error("Failed to push revert commit.")
        console.error(f"Error: {result.stderr}")
        console.error("Push manually: git push")
        return False


def _show_rollback_plan(
    tag: str,
    exists_locally: bool,
    exists_remotely: bool,
    revert_bump: bool,
    is_bump: bool,
    previous_tag: str | None,
    tag_details: dict[str, str],
) -> None:
    """Display the rollback plan to the user.

    Args:
        tag: Tag being rolled back.
        exists_locally: Whether the tag exists locally.
        exists_remotely: Whether the tag exists on remote.
        revert_bump: Whether to revert the bump commit.
        is_bump: Whether the tagged commit appears to be a bump commit.
        previous_tag: The previous version tag, if any.
        tag_details: Details about the tag (hash, date, message).
    """
    header = typer.style("Rollback Plan", fg=typer.colors.YELLOW, bold=True)
    console.info(f"\n{'─' * 50}")
    console.info(f"  {header}")
    console.info(f"{'─' * 50}")

    tag_styled = typer.style(tag, fg=typer.colors.RED, bold=True)
    console.info(f"\n  Tag to rollback: {tag_styled}")

    if tag_details:
        console.info(f"  Commit:  {tag_details.get('hash', 'unknown')[:8]}")
        console.info(f"  Date:    {tag_details.get('date', 'unknown')}")
        console.info(f"  Message: {tag_details.get('message', 'unknown')}")

    console.info(f"\n  {typer.style('Actions:', fg=typer.colors.CYAN, bold=True)}")

    step = 1
    if exists_remotely:
        console.info(f"  {step}. Delete remote tag: git push origin :refs/tags/{tag}")
        step += 1
    if exists_locally:
        console.info(f"  {step}. Delete local tag:  git tag -d {tag}")
        step += 1
    if revert_bump and is_bump:
        console.info(f"  {step}. Revert bump commit (creates a new revert commit)")
        step += 1
        console.info(f"  {step}. Push revert commit to remote")
        step += 1

    if previous_tag:
        prev_styled = typer.style(previous_tag, fg=typer.colors.GREEN, bold=True)
        console.info(f"\n  Previous version: {prev_styled}")
    else:
        console.info("\n  No previous version tag found.")

    console.info(f"\n{'─' * 50}")


def _confirm_rollback(non_interactive: bool) -> bool:
    """Confirm rollback with the user.

    Args:
        non_interactive: If True, skip confirmation.

    Returns:
        True if user confirms (or non-interactive mode).
    """
    if non_interactive:
        return True

    try:
        return bool(
            qs.confirm(
                "Proceed with rollback? This action cannot be undone.",
                default=False,
                style=_COOL_STYLE,
            ).ask()
        )
    except EOFError:
        logger.debug("Running in non-interactive environment, proceeding")
        return True


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
                style=_COOL_STYLE,
            ).ask()
        )
    except EOFError:
        logger.debug("Running in non-interactive environment")
        return False


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
    success = True

    # Delete remote tag first to stop any in-progress release
    if exists_remotely:
        if not _delete_remote_tag(tag, dry_run):
            success = False
            if not dry_run:
                console.error("Failed to delete remote tag. Aborting remaining steps.")
                console.error("You can retry or manually delete with:")
                console.error(f"  git push origin :refs/tags/{tag}")
                raise typer.Exit(code=1)

    # Delete local tag
    if exists_locally:
        if not _delete_local_tag(tag, dry_run):
            success = False
            if not dry_run:
                console.warning(f"Failed to delete local tag. Delete manually: git tag -d {tag}")

    # Revert bump commit and push (if requested)
    if revert_bump and is_bump and exists_locally:
        if not _revert_bump_commit(tag, dry_run):
            success = False
            if not dry_run:
                console.warning("Bump revert failed. Tags were still deleted.")
                console.warning("You may need to manually revert the bump commit.")
        else:
            if not _push_revert(dry_run, non_interactive):
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
    if not Path("pyproject.toml").exists():
        console.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)

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
