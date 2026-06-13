"""Git operations specific to the bump command.

This module wraps the git plumbing that ``bump_command`` uses: switching to a
target branch before bumping, pushing the resulting commit to the remote, and
restoring the original branch afterwards. Keeping these side-effecting git calls
separate from the pure orchestration in ``bump.py`` makes each piece easier to
test in isolation.

All symbols defined here are re-exported by ``bump.py`` so the public import
surface is unchanged.
"""

from __future__ import annotations

import questionary as qs
import typer
from loguru import logger

from rhiza_tools import console
from rhiza_tools.commands._shared import (
    COOL_STYLE,
    NON_INTERACTIVE_ERRORS,
    run_git_command,
)


def _handle_branch_checkout(branch: str | None, dry_run: bool) -> str | None:
    """Handle branch checkout if specified.

    Args:
        branch: Branch to checkout, or None.
        dry_run: If True, only simulate checkout.

    Returns:
        Original branch name if we switched, None otherwise.

    Raises:
        typer.Exit: If checkout fails.
    """
    if not branch:
        return None

    # Get current branch
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False)
    if result.returncode != 0:
        return None

    current_branch = result.stdout.strip()
    if current_branch == branch:
        return None

    console.info(f"Switching from {current_branch} to {branch}")
    if not dry_run:
        result = run_git_command(["git", "checkout", branch], check=False)
        if result.returncode != 0:
            console.error(f"Failed to checkout branch {branch}: {result.stderr}")
            console.error(f"Ensure the branch '{branch}' exists: git branch -a")
            raise typer.Exit(code=1)
    else:
        console.info(f"[DRY-RUN] Would checkout branch {branch}")

    return current_branch


def _handle_push_to_remote(version: str | None) -> None:
    """Handle pushing changes to remote.

    Args:
        version: Version argument (None means interactive mode).

    Raises:
        typer.Exit: If push fails.
    """
    # Interactive prompt if not in non-interactive mode and version was not specified
    if not version:
        try:
            if not qs.confirm("Push changes to remote?", default=False, style=COOL_STYLE).ask():
                console.info("Push cancelled by user")
                return
        except NON_INTERACTIVE_ERRORS:
            # In testing or non-interactive environment, do not proceed with push
            console.info("Push cancelled - non-interactive environment detected")
            logger.debug("Running in non-interactive environment, skipping push")
            return

    console.info("Pushing changes to remote...")
    result = run_git_command(["git", "push"], check=False)
    if result.returncode == 0:
        console.success("Changes pushed to remote successfully!")
    else:
        console.error(f"Failed to push changes: {result.stderr}")
        console.error("The version bump has been applied locally but could not be pushed.")
        console.error("To recover:")
        console.error("  Push manually:   git push")
        console.error("  Or undo bump:    git reset --hard HEAD~1")
        raise typer.Exit(code=1)


def _restore_original_branch(original_branch: str | None, dry_run: bool) -> None:
    """Restore original branch if we switched.

    Args:
        original_branch: Original branch to restore, or None.
        dry_run: If True, don't actually restore (since we didn't actually switch).
    """
    if original_branch and not dry_run:
        console.info(f"Returning to original branch {original_branch}")
        run_git_command(["git", "checkout", original_branch], check=False)
