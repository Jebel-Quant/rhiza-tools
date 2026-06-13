"""Git tag and commit plumbing for the rollback command.

These helpers wrap the read-only git queries (tag commit, details, history) and
the tag/commit mutations (delete local/remote tag, revert) that rollback needs.
They contain no interactive prompts, so they live apart from the orchestration
and UI in ``rollback.py``, which re-exports them for its callers and tests.
"""

from __future__ import annotations

from rhiza_tools import console
from rhiza_tools.commands._shared import run_git_command


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


def _revert_bump_commit(commit_hash: str, dry_run: bool) -> bool:
    """Revert the version bump commit.

    Creates a new revert commit rather than rewriting history, making
    this safe even when the commit has been pushed to remote.

    Args:
        commit_hash: The commit hash to revert.
        dry_run: If True, only simulate the revert.

    Returns:
        True if revert succeeded (or would succeed in dry-run).
    """
    if dry_run:
        result = run_git_command(
            ["git", "log", "-1", "--format=%s", commit_hash],
            check=False,
        )
        commit_msg = result.stdout.strip() if result.returncode == 0 else "unknown"
        console.info(f"[DRY-RUN] Would revert commit {commit_hash[:8]}: {commit_msg}")
        return True

    console.info(f"Reverting bump commit {commit_hash[:8]}...")
    result = run_git_command(
        ["git", "revert", "--no-edit", commit_hash],
        check=False,
    )
    if result.returncode == 0:
        console.success(f"Reverted bump commit: {commit_hash[:8]}")
        return True
    else:
        console.error(f"Failed to revert commit {commit_hash[:8]}")
        console.error(f"Error: {result.stderr}")
        console.error("You may need to resolve conflicts manually:")
        console.error(f"  git revert {commit_hash[:8]}")
        return False
