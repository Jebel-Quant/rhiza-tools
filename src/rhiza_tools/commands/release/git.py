"""Git plumbing for the release command.

This module holds every git-facing helper used by ``release_command``: verifying
the working tree, checking branch sync status, resolving the default remote
branch, looking up and pushing tags, and confirming with the user before the
final push. None of these functions perform interactive version selection —
that concern lives in ``release/versioning.py``.

All symbols defined here are re-exported by ``release.py`` so the public import
surface is unchanged.
"""

from __future__ import annotations

import typer

from rhiza_tools import console
from rhiza_tools.commands._git import check_tag_exists as check_tag_exists
from rhiza_tools.commands._git import run_git_command

# Number of fields in the `%H|%ci|%s` git-show format (commit hash, date, subject).
_TAG_DETAIL_FIELDS = 3
# Cap on how many commits are listed when previewing a release.
_MAX_COMMITS_SHOWN = 10


def get_current_branch() -> str:
    """Get the current git branch name for the release flow.

    Returns:
        The current branch name (e.g. ``"main"``).

    Raises:
        typer.Exit: If the branch cannot be determined.

    Example:
        >>> get_current_branch()  # doctest: +SKIP
        'main'
    """
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return result.stdout.strip()


def check_clean_working_tree() -> None:
    """Verify that the working tree is clean (no uncommitted changes).

    Raises:
        typer.Exit: If there are uncommitted changes in the working tree.

    Example:
        >>> check_clean_working_tree()  # doctest: +SKIP
    """
    result = run_git_command(["git", "status", "--porcelain"])
    if result.stdout.strip():
        console.error("You have uncommitted changes:")
        console.error(result.stdout)
        console.error("Please commit or stash your changes before releasing.")
        raise typer.Exit(code=1)


def check_branch_status(current_branch: str) -> None:
    """Check if the current branch is up-to-date with remote.

    Args:
        current_branch: The name of the current git branch.

    Raises:
        typer.Exit: If branch is behind remote or has diverged.

    Example:
        >>> check_branch_status("main")  # doctest: +SKIP
    """
    # Fetch latest from remote
    console.info("Checking remote status...")
    run_git_command(["git", "fetch", "origin"])

    # Get upstream tracking branch
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if result.returncode != 0:
        console.error(f"No upstream branch configured for {current_branch}")
        console.error(f"Set upstream with: git push -u origin {current_branch}")
        raise typer.Exit(code=1)

    upstream = result.stdout.strip()

    # Get commit hashes
    local = run_git_command(["git", "rev-parse", "@"]).stdout.strip()
    remote = run_git_command(["git", "rev-parse", upstream]).stdout.strip()
    base = run_git_command(["git", "merge-base", "@", upstream]).stdout.strip()

    if local != remote:
        if local == base:
            # Local is behind remote (need to pull)
            console.error(f"Your branch is behind '{upstream}'.")
            console.error("Pull the latest changes before releasing:")
            console.error(f"  git pull origin {current_branch}")
            raise typer.Exit(code=1)
        # Either local is ahead of remote OR branches have diverged
        # Check if remote == base to distinguish between the two cases
        elif remote == base:
            # Local is ahead of remote (need to push)
            console.warning(f"Your branch is ahead of '{upstream}'.")
            console.info("Unpushed commits:")
            result = run_git_command(["git", "log", "--oneline", "--graph", "--decorate", f"{upstream}..HEAD"])
            console.info(result.stdout)
            console.warning("Please push changes to remote before releasing.")
            raise typer.Exit(code=1)
        else:
            # Branches have diverged (need to merge or rebase)
            console.error(f"Your branch has diverged from '{upstream}'.")
            console.error("To reconcile, choose one of:")
            console.error(f"  Rebase: git pull --rebase origin {current_branch}")
            console.error(f"  Merge:  git merge origin/{current_branch}")
            console.error("Then resolve any conflicts and retry.")
            raise typer.Exit(code=1)


def get_default_branch() -> str:
    """Get the default branch name from the remote repository.

    Returns:
        The name of the default branch (e.g., "main" or "master").

    Raises:
        typer.Exit: If the default branch cannot be determined.

    Example:
        >>> branch = get_default_branch()  # doctest: +SKIP
        >>> print(branch)  # doctest: +SKIP
        main
    """
    result = run_git_command(["git", "remote", "show", "origin"], check=False)
    if result.returncode != 0:
        console.error("Could not determine default branch from remote")
        raise typer.Exit(code=1)

    for line in result.stdout.split("\n"):
        if "HEAD branch" in line:
            return str(line.split()[-1])

    console.error("Could not determine default branch from remote")
    raise typer.Exit(code=1)


def push_tag(tag: str, dry_run: bool = False) -> None:
    """Push a git tag to the remote repository.

    Args:
        tag: The tag name to push.
        dry_run: If True, only show what would be done.

    Raises:
        typer.Exit: If push fails.

    Example:
        >>> push_tag("v1.0.0")  # doctest: +SKIP
    """
    command = ["git", "push", "origin", f"refs/tags/{tag}"]

    if dry_run:
        dry_run_header = typer.style("[DRY-RUN] Would execute:", fg=typer.colors.YELLOW, bold=True)
        console.info(f"\n{dry_run_header} {' '.join(command)}")

        tag_styled = typer.style(tag, fg=typer.colors.GREEN, bold=True)
        console.info(f"[DRY-RUN] Release tag {tag_styled} would be pushed to remote")
        console.info("[DRY-RUN] This would trigger the release workflow")

        # Show what would be pushed
        result = run_git_command(["git", "show", "-s", "--format=%H %s", tag], check=False)
        if result.returncode == 0 and result.stdout.strip():
            console.info(f"[DRY-RUN] Tag points to: {result.stdout.strip()}")
    else:
        console.info(f"\n{typer.style('Pushing tag to remote...', fg=typer.colors.CYAN, bold=True)}")
        console.info(f"Command: {' '.join(command)}")
        run_git_command(command)

        tag_styled = typer.style(tag, fg=typer.colors.GREEN, bold=True)
        success_msg = (
            f"\n{typer.style('✓', fg=typer.colors.GREEN, bold=True)} Release tag {tag_styled} pushed to remote!"
        )
        console.success(success_msg)
        console.info("The release workflow will now be triggered automatically.")

    # Get repository URL for GitHub Actions link
    result = run_git_command(["git", "remote", "get-url", "origin"])
    repo_url = result.stdout.strip()

    # Try to extract GitHub repository path for displaying the Actions URL
    # Support both SSH (git@github.com:user/repo.git) and HTTPS (https://github.com/user/repo.git) formats
    repo_path = None
    if repo_url.startswith("git@github.com:"):
        # SSH format: git@github.com:user/repo.git
        repo_path = repo_url[len("git@github.com:") :].rstrip(".git")
    elif repo_url.startswith("https://github.com/"):
        # HTTPS format: https://github.com/user/repo.git
        repo_path = repo_url[len("https://github.com/") :].rstrip(".git")

    if repo_path:
        console.info(f"Monitor progress at: https://github.com/{repo_path}/actions")


def _validate_tag_state(tag: str, current_version: str) -> None:
    """Validate that tag exists locally but not remotely.

    Args:
        tag: Tag name to check.
        current_version: Current version string.

    Raises:
        typer.Exit: If tag state is invalid.
    """
    exists_locally, exists_remotely = check_tag_exists(tag)

    if exists_remotely:
        console.error(f"Tag '{tag}' already exists on remote")
        console.error(f"The release for version {current_version} has already been published.")
        console.error("If this was unintentional, you can delete the remote tag and retry:")
        console.error(f"  git push origin :refs/tags/{tag}")
        raise typer.Exit(code=1)

    if not exists_locally:
        console.error(f"Tag '{tag}' does not exist locally")
        console.error("Create the tag by bumping the version with commit enabled:")
        console.error("  rhiza-tools bump <version> --commit")
        console.error("Or use release with --bump to do both at once:")
        console.error("  rhiza-tools release --bump <PATCH|MINOR|MAJOR> --push")
        raise typer.Exit(code=1)

    console.success(f"Tag '{tag}' found locally")

    # Show tag details
    result = run_git_command(["git", "show", "-s", "--format=%H|%ci|%s", tag], check=False)
    if result.returncode == 0 and result.stdout.strip():
        parts = result.stdout.strip().split("|")
        if len(parts) == _TAG_DETAIL_FIELDS:
            commit_hash, commit_date, commit_msg = parts
            console.info(f"  Commit: {commit_hash[:8]}")
            console.info(f"  Date: {commit_date}")
            console.info(f"  Message: {commit_msg}")


def _show_commits_since_last_tag(tag: str) -> None:
    """Show commits included since the last tag.

    Args:
        tag: Current tag.
    """
    result = run_git_command(["git", "tag", "--sort=-version:refname", "--merged", "HEAD"], check=False)
    if result.returncode != 0:
        return

    tags = [t.strip() for t in result.stdout.split("\n") if t.strip() and t.strip() != tag]
    if not tags:
        return

    last_tag = tags[0]  # Most recent tag (excluding current)

    # Get commit list
    log_result = run_git_command(
        ["git", "log", f"{last_tag}..{tag}", "--oneline", "--no-decorate"],
        check=False,
    )
    if log_result.returncode == 0 and log_result.stdout.strip():
        commits = log_result.stdout.strip().split("\n")
        console.info(f"\nCommits included in this release (since {last_tag}):")
        for commit in commits[:_MAX_COMMITS_SHOWN]:
            console.info(f"  • {commit}")
        if len(commits) > _MAX_COMMITS_SHOWN:
            console.info(f"  ... and {len(commits) - _MAX_COMMITS_SHOWN} more")


def _confirm_and_push_tag(
    tag: str,
    push: bool,
    dry_run: bool,
    non_interactive: bool,
    bump_branch: str | None = None,
) -> None:
    """Confirm with user and push tag to remote.

    When *bump_branch* is provided the bump commit is pushed to the remote
    **before** the tag so that the tag references a commit that exists on
    the remote.

    Args:
        tag: Tag to push.
        push: If True, push without confirmation.
        dry_run: If True, only simulate push.
        non_interactive: If True, skip confirmation.
        bump_branch: If set, push this branch first (bump commit).

    Raises:
        typer.Exit: If user declines to push.
    """
    should_push = push
    if not non_interactive and not push:
        should_push = typer.confirm("Push tag to remote and trigger release workflow?", default=False)
        if not should_push:
            console.info("Release cancelled by user")
            raise typer.Exit(code=0)

    if should_push:
        if dry_run:
            if bump_branch:
                console.info(f"[DRY-RUN] Would push bump commit on '{bump_branch}' to remote")
            console.info(f"[DRY-RUN] Would push tag '{tag}' to remote")
        else:
            # Push the bump commit first so the tag references a known commit
            if bump_branch:
                console.info("Pushing bump commit to remote...")
                run_git_command(["git", "push", "origin", bump_branch])
            push_tag(tag, dry_run=False)
