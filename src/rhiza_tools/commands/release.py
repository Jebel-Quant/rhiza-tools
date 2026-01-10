"""Command to create a git tag and push to remote to trigger the release workflow."""

import subprocess
import sys
from pathlib import Path

import questionary as qs
import tomlkit
import typer
from loguru import logger

from rhiza_tools.config import CONFIG_FILENAME

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


def run_command(cmd: list[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(cmd)}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")
        raise typer.Exit(code=1)


def get_current_version() -> str:
    """Read current version from pyproject.toml."""
    try:
        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())
            return data["project"]["version"]
    except Exception as e:
        logger.error(f"Failed to read version from pyproject.toml: {e}")
        raise typer.Exit(code=1)


def prompt_continue(message: str = "") -> None:
    """Prompt user to continue or abort."""
    if message:
        prompt_text = f"{message} Continue?"
    else:
        prompt_text = "Continue?"
    
    if not qs.confirm(prompt_text, default=False, style=_COOL_STYLE).ask():
        logger.info("Aborted by user")
        raise typer.Exit(code=0)


def check_git_status() -> None:
    """Check if there are uncommitted changes."""
    result = run_command(["git", "status", "--porcelain"])
    if result.stdout.strip():
        logger.error("You have uncommitted changes:")
        run_command(["git", "status", "--short"], capture_output=False)
        logger.error("Please commit or stash your changes before releasing.")
        raise typer.Exit(code=1)


def get_current_branch() -> str:
    """Get the current git branch name."""
    result = run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch = result.stdout.strip()
    if not branch:
        logger.error("Could not determine current branch")
        raise typer.Exit(code=1)
    return branch


def get_default_branch() -> str:
    """Get the default branch from remote."""
    result = run_command(["git", "remote", "show", "origin"])
    for line in result.stdout.split("\n"):
        if "HEAD branch" in line:
            branch = line.split()[-1]
            if branch:
                return branch
    logger.error("Could not determine default branch from remote")
    raise typer.Exit(code=1)


def check_branch(current_branch: str) -> None:
    """Check if current branch matches default branch and prompt if not."""
    default_branch = get_default_branch()
    
    if current_branch != default_branch:
        logger.warning(f"You are on branch '{current_branch}' but the default branch is '{default_branch}'")
        logger.warning("Releases are typically created from the default branch.")
        prompt_continue(f"Proceed with release from '{current_branch}'?")


def check_upstream_status(current_branch: str) -> None:
    """Check if branch is up-to-date with remote and handle push if needed."""
    logger.info("Checking remote status...")
    run_command(["git", "fetch", "origin"])
    
    # Get upstream tracking branch
    result = run_command(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        check=False
    )
    
    if result.returncode != 0:
        logger.error(f"No upstream branch configured for {current_branch}")
        raise typer.Exit(code=1)
    
    upstream = result.stdout.strip()
    
    # Get commit SHAs for comparison
    local = run_command(["git", "rev-parse", "@"]).stdout.strip()
    remote = run_command(["git", "rev-parse", upstream]).stdout.strip()
    base = run_command(["git", "merge-base", "@", upstream]).stdout.strip()
    
    if local != remote:
        if local == base:
            # Local is behind remote
            logger.error(f"Your branch is behind '{upstream}'. Please pull changes.")
            raise typer.Exit(code=1)
        elif remote == base:
            # Local is ahead of remote
            logger.warning(f"Your branch is ahead of '{upstream}'.")
            logger.info("Unpushed commits:")
            run_command(
                ["git", "log", "--oneline", "--graph", "--decorate", f"{upstream}..HEAD"],
                capture_output=False
            )
            prompt_continue("Push changes to remote before releasing?")
            run_command(["git", "push", "origin", current_branch], capture_output=False)
        else:
            # Branches have diverged
            logger.error(f"Your branch has diverged from '{upstream}'. Please reconcile.")
            raise typer.Exit(code=1)


def check_tag_exists(tag: str) -> tuple[bool, bool]:
    """Check if tag exists locally and remotely.
    
    Returns:
        Tuple of (exists_locally, exists_remotely)
    """
    # Check local
    result = run_command(["git", "rev-parse", tag], check=False)
    exists_locally = result.returncode == 0
    
    # Check remote
    result = run_command(
        ["git", "ls-remote", "--exit-code", "--tags", "origin", f"refs/tags/{tag}"],
        check=False
    )
    exists_remotely = result.returncode == 0
    
    return exists_locally, exists_remotely


def is_gpg_signing_enabled() -> bool:
    """Check if GPG signing is configured."""
    result = run_command(["git", "config", "--get", "user.signingkey"], check=False)
    if result.returncode == 0 and result.stdout.strip():
        return True
    
    result = run_command(["git", "config", "--get", "commit.gpgsign"], check=False)
    if result.returncode == 0 and result.stdout.strip() == "true":
        return True
    
    return False


def create_tag(tag: str, version: str) -> None:
    """Create a git tag."""
    logger.info(f"Creating tag '{tag}' for version {version}")
    prompt_continue()
    
    if is_gpg_signing_enabled():
        logger.info("GPG signing is enabled. Creating signed tag.")
        run_command(["git", "tag", "-s", tag, "-m", f"Release {tag}"], capture_output=False)
    else:
        logger.info("GPG signing is not enabled. Creating unsigned tag.")
        run_command(["git", "tag", "-a", tag, "-m", f"Release {tag}"], capture_output=False)
    
    logger.success(f"Tag '{tag}' created locally")


def get_last_tag() -> str:
    """Get the last tag in the repository."""
    result = run_command(["git", "describe", "--tags", "--abbrev=0"], check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def push_tag(tag: str) -> None:
    """Push tag to remote."""
    logger.info(f"Pushing tag '{tag}' to origin will trigger the release workflow.")
    
    # Show what commits are in this tag compared to the last tag
    last_tag = get_last_tag()
    if last_tag and last_tag != tag:
        result = run_command(["git", "rev-list", f"{last_tag}..{tag}", "--count"], check=False)
        if result.returncode == 0:
            commit_count = result.stdout.strip()
            logger.info(f"Commits since {last_tag}: {commit_count}")
    
    prompt_continue()
    
    # Push the tag
    run_command(["git", "push", "origin", f"refs/tags/{tag}"], capture_output=False)
    
    # Get repository URL for GitHub Actions link
    result = run_command(["git", "remote", "get-url", "origin"])
    repo_url = result.stdout.strip()
    
    # Extract user/repo from URL
    # Handles both git@github.com:user/repo.git and https://github.com/user/repo.git
    if "github.com" in repo_url:
        import re
        match = re.search(r"github\.com[:/](.+)\.git", repo_url)
        if match:
            repo_path = match.group(1)
            logger.success(f"Release tag {tag} pushed to remote!")
            logger.info("The release workflow will now be triggered automatically.")
            logger.info(f"Monitor progress at: https://github.com/{repo_path}/actions")
            return
    
    logger.success(f"Release tag {tag} pushed to remote!")


def release_command(
    dry_run: bool = False,
):
    """Create a git tag and push to remote to trigger the release workflow."""
    # Check if pyproject.toml exists
    if not Path("pyproject.toml").exists():
        logger.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)
    
    # Get current version
    current_version = get_current_version()
    tag = f"v{current_version}"
    
    logger.info(f"Current version: {typer.style(current_version, fg=typer.colors.CYAN, bold=True)}")
    logger.info(f"Tag to create: {typer.style(tag, fg=typer.colors.CYAN, bold=True)}")
    
    if dry_run:
        logger.info("[DRY RUN] Would perform the following steps:")
        logger.info(f"  1. Check git status (uncommitted changes)")
        logger.info(f"  2. Check current branch and compare with default branch")
        logger.info(f"  3. Check if branch is up-to-date with remote")
        logger.info(f"  4. Check if tag '{tag}' already exists")
        logger.info(f"  5. Create tag '{tag}'")
        logger.info(f"  6. Push tag '{tag}' to remote")
        return
    
    # Get current branch
    current_branch = get_current_branch()
    
    # Check for uncommitted changes
    check_git_status()
    
    # Check if on default branch (with option to proceed)
    check_branch(current_branch)
    
    # Check if branch is up-to-date with remote
    check_upstream_status(current_branch)
    
    # Check if tag already exists
    exists_locally, exists_remotely = check_tag_exists(tag)
    
    if exists_remotely:
        logger.error(f"Tag '{tag}' already exists on remote")
        logger.error(f"The release for version {current_version} has already been published.")
        raise typer.Exit(code=1)
    
    skip_tag_create = False
    if exists_locally:
        logger.warning(f"Tag '{tag}' already exists locally")
        prompt_continue("Tag exists. Skip tag creation and proceed to push?")
        skip_tag_create = True
    
    # Step 1: Create the tag (if it doesn't exist)
    if not skip_tag_create:
        typer.echo("")
        typer.echo(typer.style("=== Step 1: Create Tag ===", fg=typer.colors.BLUE, bold=True))
        create_tag(tag, current_version)
    
    # Step 2: Push the tag to remote
    typer.echo("")
    typer.echo(typer.style("=== Step 2: Push Tag to Remote ===", fg=typer.colors.BLUE, bold=True))
    push_tag(tag)
