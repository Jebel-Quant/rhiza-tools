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
from loguru import logger

from rhiza_tools import console
from rhiza_tools.commands._shared import (
    run_git_command,
)
from rhiza_tools.commands.bump import (
    BumpOptions,
    Language,
    bump_command,
    get_bumped_version_from_type,
    get_current_version,
    get_interactive_bump_type,
)


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
        else:
            # Either local is ahead of remote OR branches have diverged
            # Check if remote == base to distinguish between the two cases
            if remote == base:
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


def check_tag_exists(tag: str) -> tuple[bool, bool]:
    """Check if a tag exists locally and/or remotely.

    Args:
        tag: The tag name to check.

    Returns:
        Tuple of (exists_locally, exists_remotely).

    Example:
        >>> local, remote = check_tag_exists("v1.0.0")  # doctest: +SKIP
        >>> if remote:  # doctest: +SKIP
        ...     print("Tag already released")  # doctest: +SKIP
    """
    # Check local
    result = run_git_command(["git", "rev-parse", tag], check=False)
    exists_locally = result.returncode == 0

    # Check remote
    result = run_git_command(["git", "ls-remote", "--exit-code", "--tags", "origin", f"refs/tags/{tag}"], check=False)
    exists_remotely = result.returncode == 0

    return exists_locally, exists_remotely


def push_tag(tag: str, dry_run: bool = False, non_interactive: bool = False) -> None:
    """Push a git tag to the remote repository.

    Args:
        tag: The tag name to push.
        dry_run: If True, only show what would be done.
        non_interactive: If True, skip confirmation prompts.

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
    current_version_str = get_current_version(language)
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
        current_version_str = get_current_version(language)
        current_semver = semver.Version.parse(current_version_str)
        return True, str(current_semver.bump_patch())

    current_version_str = get_current_version(language)
    try:
        new_version = get_interactive_bump_type(current_version_str)
    except (typer.Exit, EOFError):
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
    except EOFError:
        logger.debug("Running in non-interactive environment")
        return False, None

    if not should_bump:
        return False, None

    current_version_str = get_current_version(language)
    try:
        new_version = get_interactive_bump_type(current_version_str)
    except (typer.Exit, EOFError):
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
        if len(parts) == 3:
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
        for commit in commits[:10]:  # Show first 10
            console.info(f"  • {commit}")
        if len(commits) > 10:
            console.info(f"  ... and {len(commits) - 10} more")


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
            push_tag(tag, dry_run=False, non_interactive=non_interactive or push)


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


def release_command(
    bump_type: str | None = None,
    push: bool = False,
    dry_run: bool = False,
    non_interactive: bool = False,
    with_bump: bool = False,
    language: Language | None = None,
    config: Path | None = None,
) -> None:
    """Push a release tag to remote.

    This command performs the following steps:
    1. Detects the project language (Python or Go) unless explicitly specified
    2. Optionally bumps the version if bump_type is provided or with_bump is True
    3. Reads the current version from pyproject.toml (Python) or VERSION file (Go)
    4. Validates the git repository state (clean working tree, up-to-date with remote)
    5. Checks that a tag exists for the current version (created by bump-my-version)
    6. Pushes the tag to remote, triggering the release workflow

    Args:
        bump_type: Optional bump type (MAJOR, MINOR, PATCH) to apply before release.
        push: If True, push changes without prompting.
        dry_run: If True, show what would be done without making any changes.
        non_interactive: If True, skip all confirmation prompts.
        with_bump: If True, enable interactive bump selection (works with dry-run).
        language: Programming language (python or go). Auto-detected if not specified.
        config: Optional path to the .cfg.toml bumpversion config file.

    Raises:
        typer.Exit: If no supported project files are found, repository is not clean,
            tag doesn't exist, or any git operations fail.

    Example:
        Push a release tag::

            release_command()

        Preview what would happen::

            release_command(dry_run=True)

        Non-interactive mode::

            release_command(non_interactive=True)

        Bump and release::

            release_command(bump_type="MINOR", push=True)

        Interactive bump with dry-run::

            release_command(with_bump=True, push=True, dry_run=True)

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
        from rhiza_tools.commands.bump import _validate_project_exists

        _validate_project_exists(language)

    # Get current branch early
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    current_branch = result.stdout.strip()
    console.info(f"Current branch: {typer.style(current_branch, fg=typer.colors.CYAN, bold=True)}")

    # Interactive mode: ask if user wants to bump version
    should_bump, new_version = _get_bump_type_interactively(
        non_interactive, bump_type, dry_run, with_bump, language=language
    )

    # ── Preflight validation: check everything BEFORE making any changes ──
    default_branch = get_default_branch()
    _check_repository_state(dry_run, current_branch, default_branch)

    # If bumping, pre-validate that the new tag won't conflict with remote
    if should_bump and new_version and not dry_run:
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

    # Perform bump if requested (bump_command runs its own internal preflight)
    bumped_new_version: str | None = None
    if should_bump and new_version:
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
