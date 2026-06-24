"""Interactive UI and display helpers for the rollback command.

These helpers handle user-facing interaction and display: selecting a tag
interactively, confirming the rollback, pushing the revert commit, and
printing the rollback plan. They contain no tag-deletion or commit-revert
git operations — those live in ``rollback/git.py``.

All symbols defined here are re-exported by ``rollback.py`` so the public
import surface is unchanged.
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
from rhiza_tools.commands.release import check_tag_exists


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
            style=COOL_STYLE,
        ).ask()
    except NON_INTERACTIVE_ERRORS:
        logger.debug("Running in non-interactive environment")
        raise typer.Exit(code=1) from None

    if not choice:
        console.info("Rollback cancelled by user.")
        raise typer.Exit(code=0)

    # Extract tag name from choice string "v1.2.3 (local, remote)"
    return str(choice).split(" (")[0]


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
                style=COOL_STYLE,
            ).ask()
        except NON_INTERACTIVE_ERRORS:
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
                style=COOL_STYLE,
            ).ask()
        )
    except NON_INTERACTIVE_ERRORS:
        logger.debug("Running in non-interactive environment, proceeding")
        return True
