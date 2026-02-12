"""Command to create and push release tags using bump-my-version.

This module implements release functionality that uses bump-my-version to create
git tags and pushes them to remote, triggering the release workflow. It replaces
the functionality of release.sh with Python-based implementation using bump-my-version.

Example:
    Create and push a release tag::

        from rhiza_tools.commands.release import release_command
        release_command()

    Dry run to preview release::

        release_command(dry_run=True)
"""

import subprocess
from pathlib import Path
from typing import Any

import tomlkit
import typer
from bumpversion.bump import do_bump
from bumpversion.config import get_configuration
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


def run_git_command(command: list[str], check: bool = True) -> subprocess.CompletedProcess:
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
    result = subprocess.run(command, capture_output=True, text=True, check=False)
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
            return line.split()[-1]

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


def create_tag_with_bumpversion(current_version: str, dry_run: bool = False) -> None:
    """Create a git tag using bump-my-version.

    Uses bump-my-version to create a tag for the current version. This leverages
    bump-my-version's built-in tagging functionality including GPG signing support.

    Args:
        current_version: The current version string.
        dry_run: If True, only show what would be done.

    Raises:
        typer.Exit: If tag creation fails.

    Example:
        >>> create_tag_with_bumpversion("1.0.0")  # doctest: +SKIP
    """
    from rhiza_tools.config import CONFIG_FILENAME

    logger.info("Creating tag using bump-my-version...")

    config_path = Path(CONFIG_FILENAME)

    # Build configuration with tag enabled
    overrides: dict[str, Any] = {
        "current_version": current_version,
        "tag": True,  # Enable tagging
        "commit": False,  # Don't commit (version already bumped)
    }

    try:
        config = get_configuration(config_file=config_path, **overrides)
    except Exception as e:
        logger.error(f"Failed to load bumpversion configuration: {e}")
        raise typer.Exit(code=1) from None

    # Use bump-my-version to create the tag
    # We pass the same version as new_version to avoid changing the version
    # This just creates the tag for the current version
    try:
        do_bump(
            version_part=None,
            new_version=current_version,
            config=config,
            config_file=config_path,
            dry_run=dry_run,
        )
        if not dry_run:
            logger.success(f"Tag 'v{current_version}' created successfully")
    except Exception as e:
        logger.error(f"Failed to create tag: {e}")
        raise typer.Exit(code=1) from None


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
        logger.info(f"[DRY-RUN] Would run: {' '.join(command)}")
        logger.info(f"[DRY-RUN] Release tag {tag} would be pushed to remote")
        logger.info("[DRY-RUN] This would trigger the release workflow")
    else:
        run_git_command(command)
        logger.success(f"Release tag {tag} pushed to remote!")
        logger.info("The release workflow will now be triggered automatically.")

    # Get repository URL for GitHub Actions link
    result = run_git_command(["git", "remote", "get-url", "origin"])
    repo_url = result.stdout.strip()

    # Try to extract GitHub repository path for displaying the Actions URL
    # Support both SSH (git@github.com:user/repo.git) and HTTPS (https://github.com/user/repo.git) formats
    repo_path = None
    if repo_url.startswith("git@github.com:"):
        # SSH format: git@github.com:user/repo.git
        repo_path = repo_url[len("git@github.com:"):].rstrip(".git")
    elif repo_url.startswith("https://github.com/"):
        # HTTPS format: https://github.com/user/repo.git
        repo_path = repo_url[len("https://github.com/"):].rstrip(".git")

    if repo_path:
        logger.info(f"Monitor progress at: https://github.com/{repo_path}/actions")


def release_command(dry_run: bool = False) -> None:
    """Create and push a release tag based on the current version.

    This command performs the following steps:
    1. Reads the current version from pyproject.toml
    2. Validates the git repository state (clean working tree, up-to-date with remote)
    3. Creates a git tag for the release (v{version})
    4. Pushes the tag to remote, triggering the release workflow

    Args:
        dry_run: If True, show what would be done without making any changes.

    Raises:
        typer.Exit: If pyproject.toml is missing, repository is not clean,
            or any git operations fail.

    Example:
        Create and push a release::

            release_command()

        Preview what would happen::

            release_command(dry_run=True)
    """
    # Validate pyproject.toml exists
    if not Path("pyproject.toml").exists():
        logger.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)

    # Get current version
    current_version = get_current_version()
    tag = f"v{current_version}"

    logger.info(f"Current version: {current_version}")
    logger.info(f"Tag to create: {tag}")

    # Get current branch
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    current_branch = result.stdout.strip()

    # Check if on default branch
    default_branch = get_default_branch()
    if current_branch != default_branch:
        logger.warning(f"You are on branch '{current_branch}' but the default branch is '{default_branch}'")
        logger.warning("Releases are typically created from the default branch.")
        if not dry_run:
            response = typer.confirm(f"Proceed with release from '{current_branch}'?")
            if not response:
                logger.info("Release cancelled by user")
                raise typer.Exit(code=0)

    # Check for uncommitted changes
    check_clean_working_tree()

    # Check branch is up-to-date with remote
    check_branch_status(current_branch)

    # Check if tag exists
    exists_locally, exists_remotely = check_tag_exists(tag)

    if exists_remotely:
        logger.error(f"Tag '{tag}' already exists on remote")
        logger.error(f"The release for version {current_version} has already been published.")
        raise typer.Exit(code=1)

    skip_tag_create = False
    if exists_locally:
        logger.warning(f"Tag '{tag}' already exists locally")
        if not dry_run:
            response = typer.confirm("Tag exists. Skip tag creation and proceed to push?")
            if not response:
                logger.info("Release cancelled by user")
                raise typer.Exit(code=0)
        skip_tag_create = True

    # Create tag
    if not skip_tag_create:
        logger.info("Creating tag...")
        if not dry_run:
            response = typer.confirm(f"Create tag '{tag}' for version {current_version}?")
            if not response:
                logger.info("Release cancelled by user")
                raise typer.Exit(code=0)

        create_tag_with_bumpversion(current_version, dry_run)

    # Push tag
    logger.info("Pushing tag to remote...")
    logger.info(f"Pushing tag '{tag}' to origin will trigger the release workflow.")

    # Show commits since last tag
    result = run_git_command(["git", "describe", "--tags", "--abbrev=0"], check=False)
    if result.returncode == 0:
        last_tag = result.stdout.strip()
        if last_tag and last_tag != tag:
            count_result = run_git_command(["git", "rev-list", f"{last_tag}..{tag}", "--count"], check=False)
            if count_result.returncode == 0:
                commit_count = count_result.stdout.strip()
                logger.info(f"Commits since {last_tag}: {commit_count}")

    if not dry_run:
        response = typer.confirm("Push tag to remote and trigger release workflow?")
        if not response:
            logger.info("Release cancelled by user")
            raise typer.Exit(code=0)

    push_tag(tag, dry_run)

    if dry_run:
        logger.info("[DRY-RUN] Release process completed (no changes made)")
    else:
        logger.success("Release process completed successfully!")
