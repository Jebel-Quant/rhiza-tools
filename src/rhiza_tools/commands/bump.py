"""Command to bump version in pyproject.toml using semver and bump-my-version.

This module implements version bumping functionality with support for semantic
versioning, interactive selection, and various bump types (patch, minor, major,
prerelease variants).

Example:
    Bump to a specific version::

        from rhiza_tools.commands.bump import bump_command
        bump_command("1.2.3")

    Bump patch version with commit::

        bump_command("patch", commit=True)

    Interactive bump (no version specified)::

        bump_command(None)
"""

from pathlib import Path
from typing import Any, cast

import questionary as qs
import semver
import tomlkit
import typer
from bumpversion.bump import do_bump
from bumpversion.config import get_configuration
from bumpversion.ui import setup_logging
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

# Valid bump type keywords
_VALID_BUMP_TYPES = ["patch", "minor", "major", "prerelease", "build", "alpha", "beta", "rc", "dev"]

# Mapping of choice prefix to bump type for interactive selection
_CHOICE_PREFIX_TO_BUMP_TYPE = {
    "Patch": "patch",
    "Minor": "minor",
    "Major": "major",
    "Alpha": "alpha",
    "Beta": "beta",
    "RC": "rc",
    "Dev": "dev",
    "Prerelease": "prerelease",
    "Build": "build",
}


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
        logger.error(f"Failed to read version from pyproject.toml: {e}")
        raise typer.Exit(code=1) from None


def get_next_prerelease(current_version: semver.Version, token: str) -> semver.Version:
    """Calculate next prerelease version for a given token.

    Args:
        current_version: The current semantic version.
        token: The prerelease token (e.g., "alpha", "beta", "rc", "dev").

    Returns:
        The next prerelease version with the specified token.

    Example:
        >>> import semver
        >>> current = semver.Version.parse("1.0.0")
        >>> next_alpha = get_next_prerelease(current, "alpha")
        >>> print(next_alpha)
        1.0.1-alpha.1
    """
    if current_version.prerelease:
        if current_version.prerelease.startswith(token):
            return current_version.bump_prerelease()
        else:
            return current_version.replace(prerelease=f"{token}.1")
    else:
        return current_version.bump_patch().bump_prerelease(token=token)


def _determine_bump_type_from_choice(choice: str) -> str:
    """Extract bump type from interactive choice string.

    Args:
        choice: The choice string selected by the user (e.g., "Patch (1.0.0 -> 1.0.1)").

    Returns:
        The bump type extracted from the choice prefix (e.g., "patch").

    Example:
        >>> bump_type = _determine_bump_type_from_choice("Patch (1.0.0 -> 1.0.1)")
        >>> print(bump_type)
        patch
    """
    for prefix, bump_type in _CHOICE_PREFIX_TO_BUMP_TYPE.items():
        if choice.startswith(prefix):
            return bump_type
    return ""


def _get_interactive_bump_type(config: Any) -> str:
    """Get bump type from user through interactive prompt.

    Displays an interactive menu with all available bump types and their
    resulting versions. Returns the selected new version string.

    Args:
        config: The bumpversion configuration object containing current_version.

    Returns:
        The new version string selected by the user.

    Raises:
        typer.Exit: If the current version is invalid or user cancels selection.

    Example:
        Interactive prompt shows::

            Select bump type (Current: 1.0.0)
            > Patch (1.0.0 -> 1.0.1)
              Minor (1.0.0 -> 1.1.0)
              Major (1.0.0 -> 2.0.0)
              ...
    """
    current_version_str = config.current_version
    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        logger.error(f"Invalid semantic version in configuration: {current_version_str}")
        raise typer.Exit(code=1) from None

    next_patch = current_version.bump_patch()
    next_minor = current_version.bump_minor()
    next_major = current_version.bump_major()
    next_prerelease = current_version.bump_prerelease()
    next_build = current_version.bump_build()

    next_alpha = get_next_prerelease(current_version, "alpha")
    next_beta = get_next_prerelease(current_version, "beta")
    next_rc = get_next_prerelease(current_version, "rc")
    next_dev = get_next_prerelease(current_version, "dev")

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
        raise typer.Exit(code=0)

    # Extract the new version string from the choice
    # Format is "Label (Current -> New)"
    # We want "New"
    new_version: str = choice.split("-> ")[1].rstrip(")")
    return new_version


def _get_bumped_version_from_type(current_version: semver.Version, version_type: str) -> str:
    """Get bumped version string from version type keyword.

    Args:
        current_version: The current semantic version.
        version_type: The bump type keyword.

    Returns:
        The bumped version string.
    """
    bump_mapping = {
        "patch": current_version.bump_patch,
        "minor": current_version.bump_minor,
        "major": current_version.bump_major,
        "prerelease": current_version.bump_prerelease,
        "build": current_version.bump_build,
    }

    if version_type in bump_mapping:
        return str(bump_mapping[version_type]())
    elif version_type in ["alpha", "beta", "rc", "dev"]:
        return str(get_next_prerelease(current_version, version_type))

    return ""


def _validate_explicit_version(version: str) -> str:
    """Validate and clean explicit version string.

    Args:
        version: Version string to validate.

    Returns:
        Cleaned version string.

    Raises:
        typer.Exit: If version format is invalid.
    """
    # Strip 'v' prefix
    cleaned_version = version[1:] if version.startswith("v") else version

    # Validate explicit version
    try:
        semver.Version.parse(cleaned_version)
    except ValueError:
        logger.error(f"Invalid version format: {version}")
        logger.error("Please use a valid semantic version.")
        raise typer.Exit(code=1) from None

    return cleaned_version


def _parse_version_argument(version: str | None, current_version_str: str) -> str:
    """Parse version argument and return explicit version string.

    Converts bump type keywords (patch, minor, major, etc.) to explicit version
    strings, or validates and returns explicit version strings.

    Args:
        version: The version argument provided by the user. Can be a bump type
            keyword or an explicit version string.
        current_version_str: The current version string.

    Returns:
        The explicit version string to bump to, or empty string if version is None.

    Raises:
        typer.Exit: If the version format is invalid.

    Example:
        >>> version = _parse_version_argument("patch", "1.0.0")
        >>> print(version)
        1.0.1

        >>> version = _parse_version_argument("2.0.0", "1.0.0")
        >>> print(version)
        2.0.0
    """
    if not version:
        return ""

    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        logger.error(f"Invalid semantic version: {current_version_str}")
        raise typer.Exit(code=1) from None

    # Try to get bumped version from type keyword
    bumped_version = _get_bumped_version_from_type(current_version, version)
    if bumped_version:
        return bumped_version

    # Otherwise, it's an explicit version - validate and return
    return _validate_explicit_version(version)


def _validate_pyproject_exists() -> None:
    """Validate that pyproject.toml exists in the current directory.

    Raises:
        typer.Exit: If pyproject.toml is not found.
    """
    if not Path("pyproject.toml").exists():
        logger.error("pyproject.toml not found in current directory")
        raise typer.Exit(code=1)


def _build_configuration(current_version_str: str, allow_dirty: bool, commit: bool) -> tuple[Any, Path]:
    """Build bumpversion configuration with appropriate overrides.

    Args:
        current_version_str: The current version string.
        allow_dirty: If True, allow bumping even with uncommitted changes.
        commit: If True, automatically commit the version change to git.

    Returns:
        A tuple of (config object, config_path).

    Raises:
        typer.Exit: If configuration loading fails.
    """
    config_path = Path(CONFIG_FILENAME)
    overrides: dict[str, Any] = {"current_version": current_version_str}
    if allow_dirty:
        overrides["allow_dirty"] = True
    if commit:
        overrides["commit"] = True

    try:
        config = get_configuration(config_file=config_path, **overrides)
    except Exception as e:
        logger.error(f"Failed to load bumpversion configuration: {e}")
        raise typer.Exit(code=1) from None
    else:
        return config, config_path


def _get_files_to_modify(config: Any) -> list[Path]:
    """Get list of files that will be modified by bump-my-version.

    Args:
        config: The bumpversion configuration object.

    Returns:
        List of file paths that will be modified.
    """
    files = []
    if hasattr(config, "files_to_modify"):
        for file_config in config.files_to_modify:
            if hasattr(file_config, "filename"):
                files.append(Path(file_config.filename))
    return files


def _show_file_changes(file_path: Path, current_version: str, new_version: str) -> None:
    """Show the changes that will be made to a file.

    Args:
        file_path: Path to the file to preview.
        current_version: The current version string.
        new_version: The new version string.
    """
    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return

    try:
        content = file_path.read_text()
        lines_with_version = []

        for i, line in enumerate(content.split("\n"), 1):
            if current_version in line:
                lines_with_version.append((i, line))

        if lines_with_version:
            logger.info(f"  Changes in {typer.style(str(file_path), fg=typer.colors.CYAN, bold=True)}:")
            for line_num, old_line in lines_with_version:
                new_line = old_line.replace(current_version, new_version)
                logger.info(f"    Line {line_num}:")
                logger.info(f"      {typer.style('-', fg=typer.colors.RED)} {old_line.strip()}")
                logger.info(f"      {typer.style('+', fg=typer.colors.GREEN)} {new_line.strip()}")
    except Exception as e:
        logger.debug(f"Could not preview changes for {file_path}: {e}")


def _preview_file_modifications(config: Any, current_version: str, new_version: str) -> None:
    """Preview what changes will be made to files.

    Args:
        config: The bumpversion configuration object.
        current_version: The current version string.
        new_version: The new version string.
    """
    files = _get_files_to_modify(config)

    if files:
        logger.info(f"\n{typer.style('Files to be modified:', fg=typer.colors.YELLOW, bold=True)}")
        for file_path in files:
            _show_file_changes(file_path, current_version, new_version)
        logger.info("")  # Empty line for spacing
    else:
        # Fallback: check common files
        common_files = [Path("pyproject.toml"), Path("setup.py"), Path("setup.cfg")]
        logger.info(f"\n{typer.style('Files to be modified:', fg=typer.colors.YELLOW, bold=True)}")
        for file_path in common_files:
            if file_path.exists():
                _show_file_changes(file_path, current_version, new_version)
        logger.info("")  # Empty line for spacing


def _execute_bump(new_version_str: str, config: Any, config_path: Path, dry_run: bool, verbose: bool) -> None:
    """Execute the bump operation using bump-my-version.

    Args:
        new_version_str: The new version string to bump to.
        config: The bumpversion configuration object.
        config_path: Path to the bumpversion configuration file.
        dry_run: If True, show what would change without actually changing anything.
        verbose: If True, show detailed output from the bump-my-version tool.

    Raises:
        typer.Exit: If the bump operation fails.
    """
    logger.info("Running bump-my-version...")
    setup_logging(verbose=1 if verbose else 0)

    try:
        do_bump(
            version_part=None,
            new_version=new_version_str,
            config=config,
            config_file=config_path,
            dry_run=dry_run,
        )
    except Exception as e:
        logger.error(f"bump-my-version failed: {e}")
        raise typer.Exit(code=1) from None


def _log_bump_success(current_version_str: str, config: Any) -> None:
    """Log successful version bump and post-bump instructions.

    Args:
        current_version_str: The original version string before the bump.
        config: The bumpversion configuration object.
    """
    updated_version = get_current_version()
    success_msg = (
        f"\n{typer.style('✓', fg=typer.colors.GREEN, bold=True)} "
        f"Version bumped: {current_version_str} -> {updated_version}"
    )
    logger.success(success_msg)

    # Show which files were actually modified
    files = _get_files_to_modify(config)
    if files:
        logger.info(f"\n{typer.style('Modified files:', fg=typer.colors.CYAN, bold=True)}")
        for file_path in files:
            if file_path.exists():
                logger.info(f"  • {file_path}")
    else:
        # Show common files that typically get modified
        logger.info(f"\n{typer.style('Modified files:', fg=typer.colors.CYAN, bold=True)}")
        for file_path in [Path("pyproject.toml"), Path("setup.py"), Path("setup.cfg")]:
            if file_path.exists():
                # Check if file was actually modified by checking content
                try:
                    content = file_path.read_text()
                    if updated_version in content:
                        logger.info(f"  • {file_path}")
                except Exception:  # nosec B110 - safe to ignore file read errors
                    pass

    logger.info("\nDon't forget to run 'uv lock' to update the lockfile if needed.")


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
    import subprocess  # nosec

    if not branch:
        return None

    # Get current branch
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )  # nosec
    if result.returncode != 0:
        return None

    current_branch = result.stdout.strip()
    if current_branch == branch:
        return None

    logger.info(f"Switching from {current_branch} to {branch}")
    if not dry_run:
        result = subprocess.run(
            ["git", "checkout", branch],
            capture_output=True,
            text=True,
            check=False,
        )  # nosec
        if result.returncode != 0:
            logger.error(f"Failed to checkout branch {branch}: {result.stderr}")
            raise typer.Exit(code=1)
    else:
        logger.info(f"[DRY-RUN] Would checkout branch {branch}")

    return current_branch


def _get_current_git_branch() -> str:
    """Get the current git branch name.

    Returns:
        Current branch name or "unknown" if unable to determine.
    """
    import subprocess  # nosec

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )  # nosec
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _show_interactive_preview(
    current_version_str: str,
    new_version_str: str,
    current_git_branch: str,
    commit: bool,
    push: bool,
) -> bool:
    """Show interactive preview and get confirmation.

    Args:
        current_version_str: Current version.
        new_version_str: New version.
        current_git_branch: Current git branch.
        commit: Whether changes will be committed.
        push: Whether changes will be pushed.

    Returns:
        True if user confirms, False otherwise.
    """
    import questionary as qs

    # Show preview
    logger.info("\nPreview of changes:")
    logger.info(f"  Version: {current_version_str} → {new_version_str}")
    logger.info(f"  Branch: {current_git_branch}")
    if commit:
        logger.info("  Commit: Yes")
    if push:
        logger.info("  Push: Yes")

    # Confirm - wrap in try/except to handle testing scenarios
    try:
        return cast(bool, qs.confirm("Proceed with version bump?", default=True, style=_COOL_STYLE).ask())
    except EOFError:
        # In testing or non-interactive environment, proceed
        logger.debug("Running in non-interactive environment, proceeding automatically")
        return True


def _handle_push_to_remote(version: str | None) -> None:
    """Handle pushing changes to remote.

    Args:
        version: Version argument (None means interactive mode).

    Raises:
        typer.Exit: If push fails.
    """
    import subprocess  # nosec

    import questionary as qs

    # Interactive prompt if not in non-interactive mode and version was not specified
    if not version:
        try:
            if not qs.confirm("Push changes to remote?", default=False, style=_COOL_STYLE).ask():
                logger.info("Push cancelled by user")
                return
        except EOFError:
            # In testing or non-interactive environment, proceed
            logger.debug("Running in non-interactive environment, proceeding with push")

    logger.info("Pushing changes to remote...")
    result = subprocess.run(
        ["git", "push"],
        capture_output=True,
        text=True,
        check=False,
    )  # nosec
    if result.returncode == 0:
        logger.success("Changes pushed to remote successfully!")
    else:
        logger.error(f"Failed to push changes: {result.stderr}")
        logger.error("You can manually push with: git push")
        raise typer.Exit(code=1)


def _restore_original_branch(original_branch: str | None, dry_run: bool) -> None:
    """Restore original branch if we switched.

    Args:
        original_branch: Original branch to restore, or None.
        dry_run: If True, don't actually restore.
    """
    import subprocess  # nosec

    if original_branch and not dry_run:
        logger.info(f"Returning to original branch {original_branch}")
        subprocess.run(
            ["git", "checkout", original_branch],
            capture_output=True,
            text=True,
            check=False,
        )  # nosec


def bump_command(
    version: str | None = None,
    dry_run: bool = False,
    commit: bool = False,
    push: bool = False,
    branch: str | None = None,
    allow_dirty: bool = False,
    verbose: bool = False,
) -> None:
    """Bump version in pyproject.toml using bump-my-version.

    This function handles the complete version bumping workflow including
    configuration loading, version parsing, interactive selection (if needed),
    and executing the bump operation.

    Args:
        version: The version to bump to. Can be an explicit version (e.g., "1.2.3"),
            a bump type ("patch", "minor", "major"), a prerelease type
            ("alpha", "beta", "rc", "dev"), or None for interactive selection.
        dry_run: If True, show what would change without actually changing anything.
        commit: If True, automatically commit the version change to git.
        push: If True, push changes to remote after commit (implies commit=True).
        branch: Branch to perform the bump on (default: current branch).
        allow_dirty: If True, allow bumping even with uncommitted changes.
        verbose: If True, show detailed output from the bump-my-version tool.

    Raises:
        typer.Exit: If pyproject.toml is missing, configuration is invalid, or
            bump operation fails.

    Example:
        Bump to patch version::

            bump_command("patch")

        Bump with dry run::

            bump_command("1.2.3", dry_run=True)

        Interactive bump with commit::

            bump_command(None, commit=True)

        Bump and push to remote::

            bump_command("minor", push=True)
    """
    _validate_pyproject_exists()

    # Handle branch checkout if specified
    original_branch = _handle_branch_checkout(branch, dry_run)

    # If push is True, commit must also be True
    if push:
        commit = True

    current_version_str = get_current_version()
    config, config_path = _build_configuration(current_version_str, allow_dirty, commit)

    # Get current branch for display
    current_git_branch = _get_current_git_branch()

    logger.info(f"Current branch: {typer.style(current_git_branch, fg=typer.colors.CYAN, bold=True)}")
    logger.info(f"Current version: {typer.style(current_version_str, fg=typer.colors.CYAN, bold=True)}")

    # Determine new version string
    if version:
        new_version_str = _parse_version_argument(version, current_version_str)
    else:
        new_version_str = _get_interactive_bump_type(config)

    logger.info(f"New version will be: {typer.style(new_version_str, fg=typer.colors.GREEN, bold=True)}")

    # Show preview of file changes
    _preview_file_modifications(config, current_version_str, new_version_str)

    # Interactive preview and confirmation (only in true interactive mode)
    if not version and not dry_run:
        if not _show_interactive_preview(current_version_str, new_version_str, current_git_branch, commit, push):
            logger.info("Version bump cancelled by user")
            raise typer.Exit(code=0)

    _execute_bump(new_version_str, config, config_path, dry_run, verbose)

    if not dry_run:
        _log_bump_success(current_version_str, config)

        # Handle push
        if push:
            _handle_push_to_remote(version)

    # Restore original branch if we switched
    _restore_original_branch(original_branch, dry_run)
