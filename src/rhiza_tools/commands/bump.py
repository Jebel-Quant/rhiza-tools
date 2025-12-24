from pathlib import Path
from typing import Optional

import questionary
import semver
import tomlkit
import typer
from loguru import logger


def get_current_version() -> str:
    """Read current version from pyproject.toml."""
    try:
        with open("pyproject.toml", "r") as f:
            data = tomlkit.parse(f.read())
            return data["project"]["version"]
    except Exception as e:
        logger.error(f"Failed to read version from pyproject.toml: {e}")
        raise typer.Exit(code=1)

def update_version(new_version: str) -> None:
    """Update version in pyproject.toml."""
    try:
        with open("pyproject.toml", "r") as f:
            data = tomlkit.parse(f.read())
        
        data["project"]["version"] = new_version
        
        with open("pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(data))
            
    except Exception as e:
        logger.error(f"Failed to update pyproject.toml: {e}")
        raise typer.Exit(code=1)

def bump_command(version: Optional[str] = None, dry_run: bool = False):
    """
    Bump version in pyproject.toml using semver and tomlkit.
    """
    # Check if pyproject.toml exists
    if not Path("pyproject.toml").exists():
        logger.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)

    # Get current version
    current_version_str = get_current_version()
    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        logger.error(f"Invalid semantic version in pyproject.toml: {current_version_str}")
        raise typer.Exit(code=1)

    logger.info(f"Current version: {current_version_str}")

    bump_type = ""
    new_version_str = ""

    if version:
        # If version argument is provided
        if version in ["patch", "minor", "major"]:
            bump_type = version
        else:
            # Explicit version
            # Strip 'v' prefix
            if version.startswith("v"):
                version = version[1:]
            new_version_str = version
    else:
        # Interactive mode
        next_patch = current_version.bump_patch()
        next_minor = current_version.bump_minor()
        next_major = current_version.bump_major()

        choice = questionary.select(
            f"Select bump type (Current: {current_version_str})",
            choices=[
                f"Patch ({current_version_str} -> {next_patch})",
                f"Minor ({current_version_str} -> {next_minor})",
                f"Major ({current_version_str} -> {next_major})",
            ]
        ).ask()

        if not choice:
            raise typer.Exit(code=0)

        if choice.startswith("Patch"):
            bump_type = "patch"
        elif choice.startswith("Minor"):
            bump_type = "minor"
        elif choice.startswith("Major"):
            bump_type = "major"

    # Calculate/Validate new version
    if bump_type:
        logger.info(f"Bumping version using: {bump_type}")
        if bump_type == "patch":
            new_version_str = str(current_version.bump_patch())
        elif bump_type == "minor":
            new_version_str = str(current_version.bump_minor())
        elif bump_type == "major":
            new_version_str = str(current_version.bump_major())
    else:
        # Validate explicit version
        try:
            semver.Version.parse(new_version_str)
        except ValueError:
            logger.error(f"Invalid version format: {new_version_str}")
            logger.error("Please use a valid semantic version.")
            raise typer.Exit(code=1)

    logger.info(f"New version will be: {new_version_str}")

    if dry_run:
        logger.info("Dry run enabled. Skipping actual changes.")
        return

    # Update version in pyproject.toml
    logger.info("Updating pyproject.toml...")
    update_version(new_version_str)
    
    # Verify the update
    updated_version = get_current_version()
    if updated_version != new_version_str:
        logger.error(f"Version update failed. Expected {new_version_str} but got {updated_version}")
        raise typer.Exit(code=1)

    logger.success(f"Version bumped: {current_version_str} -> {new_version_str} in pyproject.toml")
    logger.info("Don't forget to run 'uv lock' to update the lockfile if needed.")

