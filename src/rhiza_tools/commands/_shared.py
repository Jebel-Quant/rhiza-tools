"""Shared utilities for rhiza-tools commands.

This module provides common helpers used across multiple command modules
(bump, release, rollback) to avoid duplication and ensure consistency.

Utilities:
    - COOL_STYLE: Shared questionary styling for interactive prompts
    - run_git_command: Execute git commands with standard error handling
    - get_current_version: Read the project version from pyproject.toml
    - get_current_git_branch: Safely determine the current git branch
    - validate_pyproject_exists: Guard against missing pyproject.toml
"""

import subprocess  # nosec B404 - subprocess needed for git operations
from pathlib import Path
from typing import Any, cast

import questionary as qs
import tomlkit
import typer

from rhiza_tools import console

COOL_STYLE = qs.Style(
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
        console.error(f"Git command failed: {' '.join(command)}")
        console.error(f"Error: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, command, result.stdout, result.stderr)
    return result


def get_current_version() -> str:
    """Read current version from pyproject.toml.

    Returns:
        The current version string from the project.version field.

    Raises:
        typer.Exit: If pyproject.toml cannot be read or parsed.

    Example:
        >>> version = get_current_version()  # doctest: +SKIP
        >>> print(version)  # doctest: +SKIP
        0.1.0
    """
    try:
        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())
            project = cast(dict[str, Any], data["project"])
            return str(project["version"])
    except Exception as e:
        console.error(f"Failed to read version from pyproject.toml: {e}")
        raise typer.Exit(code=1) from None


def get_current_git_branch() -> str:
    """Get the current git branch name.

    This is the safe variant that returns ``"unknown"`` on failure,
    suitable for display purposes. For strict validation use
    :func:`run_git_command` directly.

    Returns:
        Current branch name or "unknown" if unable to determine.
    """
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def validate_pyproject_exists() -> None:
    """Validate that pyproject.toml exists in the current directory.

    Raises:
        typer.Exit: If pyproject.toml is not found.
    """
    if not Path("pyproject.toml").exists():
        console.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)
