"""Command to push release tags to remote.

This module implements release functionality that validates the git repository
state and pushes tags to remote, triggering the release workflow. Tags are
created by bump-my-version during the bump process.

Example:
    Push a release tag::

        from rhiza_tools.commands.release import release_command
        release_command()

    Dry run to preview release::

        release_command(dry_run=True)
"""

import subprocess  # nosec B404 - subprocess needed for git operations
from pathlib import Path
from typing import Any, cast

import tomlkit
import typer
from loguru import logger


def get_current_version() -> str:
    """Read current version from pyproject.toml.

    Returns:
        The current version string from the project.version field.

    Raises:
        typer.Exit: If pyproject.toml cannot be read or parsed.

    Example:
        >>> version = get_current_version()  # doctest: +SKIP
        >>> print(version)  # doctest: +SKIP
        0.2.3
    """
    try:
        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())
            project: dict[str, Any] = data["project"]  # type: ignore
            return str(project["version"])
    except Exception as e:
        logger.error(f"Failed to read version from pyproject.toml: {e}")
        raise typer.Exit(code=1) from None


def run_git_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the result.

    Args:
        command: The git command to run as a list of arguments.
        check: If True, raise an exception on non-zero exit code.

    Returns:
        CompletedProcess instance with stdout, stderr, and returncode.

    Raises:
        subprocess.CalledProcessError: If check=True and command fails.

    Example:
        >>> result = run_git_command(["git", "status", "--porcelain"])  # doctest: +SKIP
        >>> print(result.stdout)  # doctest: +SKIP
    """
    result = subprocess.run(command, capture_output=True, text=True, check=False)  # nosec B603 - git commands are trusted
    if check and result.returncode != 0:
        logger.error(f"Git command failed: {' '.join(command)}")
        logger.error(f"Error: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
    return result


def check_clean_working_tree() -> None:
    """Verify that the working tree is clean (no uncommitted changes).

    Raises:
        typer.Exit: If there are uncommitted changes in the working tree.

    Example:
        >>> check_clean_working_tree()  # doctest: +SKIP
    """
    result = run_git_command(["git", "status", "--porcelain"])
    if result.stdout.strip():
        logger.error("You have uncommitted changes:")
        logger.error(result.stdout)
        logger.error("Please commit or stash your changes before releasing.")
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
    logger.info("Checking remote status...")
    run_git_command(["git", "fetch", "origin"])

    # Get upstream tracking branch
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if result.returncode != 0:
        logger.error(f"No upstream branch configured for {current_branch}")
        raise typer.Exit(code=1)

    upstream = result.stdout.strip()

    # Get commit hashes
    local = run_git_command(["git", "rev-parse", "@"]).stdout.strip()
    remote = run_git_command(["git", "rev-parse", upstream]).stdout.strip()
    base = run_git_command(["git", "merge-base", "@", upstream]).stdout.strip()

    if local != remote:
        if local == base:
            # Local is behind remote (need to pull)
            logger.error(f"Your branch is behind '{upstream}'. Please pull changes.")
            raise typer.Exit(code=1)
        else:
            # Either local is ahead of remote OR branches have diverged
            # Check if remote == base to distinguish between the two cases
            if remote == base:
                # Local is ahead of remote (need to push)
                logger.warning(f"Your branch is ahead of '{upstream}'.")
                logger.info("Unpushed commits:")
                result = run_git_command(["git", "log", "--oneline", "--graph", "--decorate", f"{upstream}..HEAD"])
                logger.info(result.stdout)
                logger.warning("Please push changes to remote before releasing.")
                raise typer.Exit(code=1)
            else:
                # Branches have diverged (need to merge or rebase)
                logger.error(f"Your branch has diverged from '{upstream}'. Please reconcile.")
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
        logger.error("Could not determine default branch from remote")
        raise typer.Exit(code=1)

    for line in result.stdout.split("\n"):
        if "HEAD branch" in line:
            return str(line.split()[-1])

    logger.error("Could not determine default branch from remote")
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
        logger.info(f"\n{dry_run_header} {' '.join(command)}")

        tag_styled = typer.style(tag, fg=typer.colors.GREEN, bold=True)
        logger.info(f"[DRY-RUN] Release tag {tag_styled} would be pushed to remote")
        logger.info("[DRY-RUN] This would trigger the release workflow")

        # Show what would be pushed
        result = run_git_command(["git", "show", "-s", "--format=%H %s", tag], check=False)
        if result.returncode == 0 and result.stdout.strip():
            logger.info(f"[DRY-RUN] Tag points to: {result.stdout.strip()}")
    else:
        logger.info(f"\n{typer.style('Pushing tag to remote...', fg=typer.colors.CYAN, bold=True)}")
        logger.info(f"Command: {' '.join(command)}")
        run_git_command(command)

        tag_styled = typer.style(tag, fg=typer.colors.GREEN, bold=True)
        success_msg = (
            f"\n{typer.style('✓', fg=typer.colors.GREEN, bold=True)} Release tag {tag_styled} pushed to remote!"
        )
        logger.success(success_msg)
        logger.info("The release workflow will now be triggered automatically.")

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
        logger.info(f"Monitor progress at: https://github.com/{repo_path}/actions")


def _prompt_for_bump_type() -> str | None:
    """Prompt user to select bump type.

    Shows the same interactive menu as the bump command with version previews.

    Returns:
        Selected bump type in uppercase (e.g., "PATCH", "MINOR", "MAJOR") or None if cancelled.
    """
    import questionary as qs
    import semver
    from rhiza_tools.commands.bump import get_next_prerelease, _COOL_STYLE

    try:
        current_version_str = get_current_version()
        try:
            current_version = semver.Version.parse(current_version_str)
        except ValueError:
            logger.error(f"Invalid semantic version: {current_version_str}")
            return None

        # Calculate next versions for each bump type
        next_patch = current_version.bump_patch()
        next_minor = current_version.bump_minor()
        next_major = current_version.bump_major()
        next_prerelease = current_version.bump_prerelease()
        next_build = current_version.bump_build()
        next_alpha = get_next_prerelease(current_version, "alpha")
        next_beta = get_next_prerelease(current_version, "beta")
        next_rc = get_next_prerelease(current_version, "rc")
        next_dev = get_next_prerelease(current_version, "dev")

        # Show the same menu as bump command
        choice = qs.select(
            f"Select bump type (Current: {current_version_str})",
            choices=[
                f"Patch ({current_version_str} -> {next_patch})",
                f"Minor ({current_version_str} -> {next_minor})",
                f"Major ({current_version_str} -> {next_major})",
                qs.Separator("-" * 30),
                f"Prerelease ({current_version_str} -> {next_prerelease})",
                f"Alpha ({current_version_str} -> {next_alpha})",
                f"Beta ({current_version_str} -> {next_beta})",
                f"RC ({current_version_str} -> {next_rc})",
                f"Dev ({current_version_str} -> {next_dev})",
                f"Build ({current_version_str} -> {next_build})",
            ],
            style=_COOL_STYLE,
        ).ask()

        if not choice:
            return None

        # Extract bump type from choice (e.g., "Patch (...)" -> "PATCH")
        bump_type = choice.split()[0].upper()
        return bump_type
    except EOFError:
        logger.debug("Running in non-interactive environment")
        return None


def _handle_with_bump_mode(non_interactive: bool) -> tuple[bool, str | None]:
    """Handle --with-bump flag logic.

    Args:
        non_interactive: If True, default to PATCH without prompting.

    Returns:
        Tuple of (should_bump, selected_bump_type).
    """
    if non_interactive:
        logger.warning("--with-bump in non-interactive mode without --bump type, defaulting to PATCH")
        return True, "PATCH"

    selected_type = _prompt_for_bump_type()
    return selected_type is not None, selected_type


def _handle_default_interactive_bump() -> tuple[bool, str | None]:
    """Handle default interactive bump selection.

    Returns:
        Tuple of (should_bump, selected_bump_type).
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
    else:
        if should_bump:
            return True, _prompt_for_bump_type()
        return False, None


def _get_bump_type_interactively(
    non_interactive: bool, bump_type: str | None, dry_run: bool, with_bump: bool = False
) -> tuple[bool, str | None]:
    """Get bump type interactively or from parameters.

    Args:
        non_interactive: If True, skip interactive prompts.
        bump_type: Explicit bump type provided.
        dry_run: If True, skip interactive prompts (unless with_bump is set).
        with_bump: If True, enable interactive bump selection even in dry-run mode.

    Returns:
        Tuple of (should_bump, selected_bump_type).
    """
    # Explicit bump type provided
    if bump_type:
        return True, bump_type.upper()

    # --with-bump flag: prompt for bump type (even in dry-run)
    if with_bump:
        return _handle_with_bump_mode(non_interactive)

    # Default interactive mode: ask if user wants to bump
    if not non_interactive and not dry_run:
        return _handle_default_interactive_bump()

    return False, None


def _calculate_new_version(selected_bump_type: str) -> str:
    """Calculate what the new version would be after bumping.

    Args:
        selected_bump_type: Bump type to apply (MAJOR, MINOR, PATCH, PRERELEASE, ALPHA, BETA, RC, DEV, BUILD).

    Returns:
        The new version string.

    Raises:
        typer.Exit: If bump type is invalid or current version is invalid.
    """
    import semver
    from rhiza_tools.commands.bump import get_next_prerelease

    current = get_current_version()
    try:
        current_semver = semver.Version.parse(current)
    except ValueError:
        logger.error(f"Invalid semantic version: {current}")
        raise typer.Exit(code=1) from None

    # Build map of all supported bump types
    bump_map: dict[str, str] = {
        "MAJOR": str(current_semver.bump_major()),
        "MINOR": str(current_semver.bump_minor()),
        "PATCH": str(current_semver.bump_patch()),
        "PRERELEASE": str(current_semver.bump_prerelease()),
        "BUILD": str(current_semver.bump_build()),
        "ALPHA": str(get_next_prerelease(current_semver, "alpha")),
        "BETA": str(get_next_prerelease(current_semver, "beta")),
        "RC": str(get_next_prerelease(current_semver, "rc")),
        "DEV": str(get_next_prerelease(current_semver, "dev")),
    }

    if selected_bump_type not in bump_map:
        valid_types = list(bump_map.keys())
        logger.error(f"Invalid bump type: {selected_bump_type}. Must be one of {valid_types}")
        raise typer.Exit(code=1)

    return bump_map[selected_bump_type]


def _perform_version_bump(selected_bump_type: str, dry_run: bool) -> str:
    """Perform version bump with validation.

    Args:
        selected_bump_type: Bump type to apply.
        dry_run: If True, only simulate the bump.

    Returns:
        The new version string (calculated even in dry-run mode).

    Raises:
        typer.Exit: If bump type is invalid.
    """
    from rhiza_tools.commands.bump import BumpOptions, bump_command

    logger.info(f"Bumping version with type: {selected_bump_type}")

    # Calculate the new version before performing the bump
    new_version = _calculate_new_version(selected_bump_type)

    # Call bump_command with BumpOptions
    bump_command(
        BumpOptions(
            version=selected_bump_type.lower(),
            dry_run=dry_run,
            commit=True,
            push=False,  # Don't push yet, we'll do it after tagging
            allow_dirty=False,
            verbose=False,
        )
    )

    if dry_run:
        logger.info("[DRY-RUN] Version would be bumped before release")

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
        logger.error(f"Tag '{tag}' already exists on remote")
        logger.error(f"The release for version {current_version} has already been published.")
        raise typer.Exit(code=1)

    if not exists_locally:
        logger.error(f"Tag '{tag}' does not exist locally")
        logger.error("Please run 'rhiza-tools bump' to create a new version with tag")
        raise typer.Exit(code=1)

    logger.success(f"Tag '{tag}' found locally")

    # Show tag details
    result = run_git_command(["git", "show", "-s", "--format=%H|%ci|%s", tag], check=False)
    if result.returncode == 0 and result.stdout.strip():
        parts = result.stdout.strip().split("|")
        if len(parts) == 3:
            commit_hash, commit_date, commit_msg = parts
            logger.info(f"  Commit: {commit_hash[:8]}")
            logger.info(f"  Date: {commit_date}")
            logger.info(f"  Message: {commit_msg}")


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
        logger.info(f"\nCommits included in this release (since {last_tag}):")
        for commit in commits[:10]:  # Show first 10
            logger.info(f"  • {commit}")
        if len(commits) > 10:
            logger.info(f"  ... and {len(commits) - 10} more")


def _confirm_and_push_tag(tag: str, push: bool, dry_run: bool, non_interactive: bool) -> None:
    """Confirm with user and push tag to remote.

    Args:
        tag: Tag to push.
        push: If True, push without confirmation.
        dry_run: If True, only simulate push.
        non_interactive: If True, skip confirmation.

    Raises:
        typer.Exit: If user declines to push.
    """
    should_push = push
    if not dry_run and not non_interactive and not push:
        should_push = typer.confirm("Push tag to remote and trigger release workflow?", default=False)
        if not should_push:
            logger.info("Release cancelled by user")
            raise typer.Exit(code=0)

    if should_push or dry_run:
        push_tag(tag, dry_run, non_interactive or push)


def _get_release_version(dry_run: bool, bumped_new_version: str | None) -> tuple[str, str]:
    """Get current version and tag for release.

    Args:
        dry_run: If True and version was bumped, use bumped version.
        bumped_new_version: New version if bump was performed.

    Returns:
        Tuple of (current_version, tag).
    """
    if dry_run and bumped_new_version:
        current_version = bumped_new_version
    else:
        current_version = get_current_version()

    tag = f"v{current_version}"
    logger.info(f"Current version: {current_version}")
    logger.info(f"Expected tag: {tag}")

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
        logger.info(f"Note: You are on branch '{current_branch}' (default branch is '{default_branch}')")

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
            logger.error(f"Tag '{tag}' already exists on remote")
            logger.error(f"The release for version {current_version} has already been published.")
            raise typer.Exit(code=1)
        logger.info(f"[DRY-RUN] Tag '{tag}' would be created by the bump and release process")
    else:
        _validate_tag_state(tag, current_version)


def release_command(
    bump_type: str | None = None,
    push: bool = False,
    dry_run: bool = False,
    non_interactive: bool = False,
    with_bump: bool = False,
) -> None:
    """Push a release tag to remote.

    This command performs the following steps:
    1. Optionally bumps the version if bump_type is provided or with_bump is True
    2. Reads the current version from pyproject.toml
    3. Validates the git repository state (clean working tree, up-to-date with remote)
    4. Checks that a tag exists for the current version (created by bump-my-version)
    5. Pushes the tag to remote, triggering the release workflow

    Args:
        bump_type: Optional bump type (MAJOR, MINOR, PATCH) to apply before release.
        push: If True, push changes without prompting.
        dry_run: If True, show what would be done without making any changes.
        non_interactive: If True, skip all confirmation prompts.
        with_bump: If True, enable interactive bump selection (works with dry-run).

    Raises:
        typer.Exit: If pyproject.toml is missing, repository is not clean,
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
    """
    # Validate pyproject.toml exists
    if not Path("pyproject.toml").exists():
        logger.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)

    # Get current branch early
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    current_branch = result.stdout.strip()
    logger.info(f"Current branch: {typer.style(current_branch, fg=typer.colors.CYAN, bold=True)}")

    # Interactive mode: ask if user wants to bump version
    should_bump, selected_bump_type = _get_bump_type_interactively(non_interactive, bump_type, dry_run, with_bump)

    # Perform bump if requested
    bumped_new_version: str | None = None
    if should_bump and selected_bump_type:
        bumped_new_version = _perform_version_bump(selected_bump_type, dry_run)

    # Get current version and tag
    current_version, tag = _get_release_version(dry_run, bumped_new_version)

    # Check repository state
    default_branch = get_default_branch()
    _check_repository_state(dry_run, current_branch, default_branch)

    # Validate tag state
    _handle_tag_validation(dry_run, bumped_new_version, tag, current_version)

    # Push tag
    logger.info("Preparing to push tag to remote...")
    logger.info(f"Pushing tag '{tag}' to origin will trigger the release workflow.")

    # Show commits since last tag (if any)
    _show_commits_since_last_tag(tag)

    # Confirm and push
    _confirm_and_push_tag(tag, push, dry_run, non_interactive)

    if dry_run:
        logger.info("[DRY-RUN] Release process completed (no changes made)")
    else:
        logger.success("Release process completed successfully!")
