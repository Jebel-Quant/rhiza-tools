"""Command to bump version using semver and bump-my-version.

This module implements version bumping functionality with support for semantic
versioning, interactive selection, and various bump types (patch, minor, major,
prerelease variants). Supports multiple languages including Python and Go.

Example:
    Bump to a specific version::

        from rhiza_tools.commands.bump import bump_command
        bump_command("1.2.3")

    Bump patch version with commit::

        bump_command("patch", commit=True)

    Interactive bump (no version specified)::

        bump_command(None)
"""

import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

import questionary as qs
import semver
import typer
from loguru import logger

from rhiza_tools import console
from rhiza_tools.commands._shared import (
    COOL_STYLE,
    NON_INTERACTIVE_ERRORS,
    get_current_git_branch,
    get_latest_remote_version,
    run_git_command,
)

# Re-export the bump-my-version adapter helpers for the same reason. Names called
# directly inside this module (bump_command) need no alias; pure re-exports use one.
from rhiza_tools.commands.bump_engine import (
    _build_changelog_hooks,
    _build_configuration,
    _execute_bump,
    _get_files_to_modify,
    _preflight_bump,
    _preview_file_modifications,
)
from rhiza_tools.commands.bump_engine import (
    _show_file_changes as _show_file_changes,
)

# Re-export pure version-math helpers so external callers and tests that reference
# ``rhiza_tools.commands.bump.<name>`` (including monkeypatch string paths) keep
# working after these moved to bump_versioning. The redundant ``as`` aliases mark
# them as intentional re-exports for ruff (F401).
from rhiza_tools.commands.bump_versioning import (
    _CHOICE_PREFIX_TO_BUMP_TYPE as _CHOICE_PREFIX_TO_BUMP_TYPE,
)
from rhiza_tools.commands.bump_versioning import (
    _VALID_BUMP_TYPES as _VALID_BUMP_TYPES,
)
from rhiza_tools.commands.bump_versioning import (
    _denormalize_pep440_to_semver as _denormalize_pep440_to_semver,
)
from rhiza_tools.commands.bump_versioning import (
    _determine_bump_type_from_choice as _determine_bump_type_from_choice,
)
from rhiza_tools.commands.bump_versioning import (
    _parse_version_argument,
)
from rhiza_tools.commands.bump_versioning import (
    _validate_explicit_version as _validate_explicit_version,
)
from rhiza_tools.commands.bump_versioning import (
    get_bumped_version_from_type as get_bumped_version_from_type,
)
from rhiza_tools.commands.bump_versioning import (
    get_next_prerelease as get_next_prerelease,
)


class Language(StrEnum):
    """Supported programming languages for version bumping.

    Attributes:
        PYTHON: Python projects using pyproject.toml
        GO: Go projects using VERSION file with go.mod
    """

    PYTHON = "python"
    GO = "go"

    @classmethod
    def detect(cls) -> "Language | None":
        """Detect the project language based on files present.

        Returns:
            Language enum if detected, None if no supported language is found.

        Example:
            >>> lang = Language.detect()  # doctest: +SKIP
            >>> if lang:
            ...     print(lang.value)  # doctest: +SKIP
            python
        """
        if Path("pyproject.toml").exists():
            return cls.PYTHON
        elif Path("go.mod").exists() and Path("VERSION").exists():
            return cls.GO
        return None

    def get_version_file(self) -> Path:
        """Get the version file path for this language.

        Returns:
            Path to the version file.

        Example:
            >>> lang = Language.PYTHON
            >>> lang.get_version_file()  # doctest: +SKIP
            PosixPath('pyproject.toml')
        """
        if self == Language.PYTHON:
            return Path("pyproject.toml")
        # Language.GO
        return Path("VERSION")


@dataclass
class BumpOptions:
    """Configuration options for bump command.

    Attributes:
        version: The version to bump to. Can be an explicit version, bump type, or None.
        dry_run: If True, show what would change without actually changing anything.
        commit: If True, automatically commit the version change to git.
        push: If True, push changes to remote after commit (implies commit=True).
        branch: Branch to perform the bump on (default: current branch).
        allow_dirty: If True, allow bumping even with uncommitted changes.
        language: The programming language (python or go). If None, auto-detect.
        config: Path to the .cfg.toml config file. Defaults to CONFIG_FILENAME.
    """

    version: str | None = None
    dry_run: bool = False
    commit: bool = False
    push: bool = False
    branch: str | None = None
    allow_dirty: bool = False
    language: Language | None = None
    config: Path | None = None


def get_current_version(language: Language) -> str:
    """Read current version from project configuration for the specified language.

    Args:
        language: The programming language (python or go).

    Returns:
        The current version string in semver format (for compatibility with bump logic).

    Raises:
        typer.Exit: If version cannot be read or parsed.

    Example:
        >>> version = get_current_version(Language.PYTHON)  # doctest: +SKIP
        >>> print(version)  # doctest: +SKIP
        0.1.0
    """
    if language == Language.PYTHON:
        try:
            with open("pyproject.toml", "rb") as f:
                data = tomllib.load(f)
            # Convert PEP 440 format back to semver format for compatibility
            # e.g., 0.1.1a1 -> 0.1.1-alpha.1
            return _denormalize_pep440_to_semver(str(data["project"]["version"]))
        except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as e:
            console.error(f"Failed to read version from pyproject.toml: {e}")
            raise typer.Exit(code=1) from None
    elif language == Language.GO:
        try:
            with open("VERSION") as f:
                version = f.read().strip()
        except OSError as e:
            console.error(f"Failed to read version from VERSION file: {e}")
            raise typer.Exit(code=1) from None

        if not version:
            console.error("VERSION file is empty")
            raise typer.Exit(code=1)

        # Validate that the version string is not just whitespace and looks valid
        if not version or version.isspace():
            console.error("VERSION file contains only whitespace")
            raise typer.Exit(code=1)

        return version
    else:
        console.error(f"Unsupported language: {language}")
        raise typer.Exit(code=1)


def get_interactive_bump_type(current_version_str: str) -> str:
    """Get bump type from user through interactive prompt.

    Displays an interactive menu with all available bump types and their
    resulting versions. Returns the selected new version string.

    Args:
        current_version_str: The current version string (semver-compatible).

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
    try:
        current_version = semver.Version.parse(current_version_str)
    except ValueError:
        console.error(f"Invalid semantic version in configuration: {current_version_str}")
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

    try:
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
            style=COOL_STYLE,
        ).ask()
    except NON_INTERACTIVE_ERRORS:
        console.error("Interactive selection not available in non-interactive environment")
        raise typer.Exit(code=1) from None

    if not choice:
        raise typer.Exit(code=0)

    # Extract the new version string from the choice
    # Format is "Label (Current -> New)"
    # We want "New"
    # Check if the choice contains the expected format (skip separators)
    if "-> " not in choice:
        console.error("Invalid choice selection")
        raise typer.Exit(code=1)

    new_version: str = choice.split("-> ")[1].rstrip(")")
    return new_version


def _validate_project_exists(language: Language) -> None:
    """Validate that required project files exist for the specified language.

    Args:
        language: The programming language (python or go).

    Raises:
        typer.Exit: If required project files are not found.
    """
    if language == Language.PYTHON:
        if not Path("pyproject.toml").exists():
            console.error("Python project detected but pyproject.toml not found.")
            console.error("Please create a pyproject.toml file with the current version.")
            raise typer.Exit(code=1)
    elif language == Language.GO:
        if not Path("go.mod").exists():
            console.error("Go language specified but go.mod not found.")
            console.error("Please create a go.mod file for your Go project.")
            raise typer.Exit(code=1)
        if not Path("VERSION").exists():
            console.error("Go project detected but VERSION file not found.")
            console.error("Please create a VERSION file with the current version.")
            raise typer.Exit(code=1)
    else:
        console.error(f"Unsupported language: {language}")
        raise typer.Exit(code=1)


def _log_bump_success(current_version_str: str, config: Any, language: Language) -> None:
    """Log successful version bump and post-bump instructions.

    Args:
        current_version_str: The original version string before the bump.
        config: The bumpversion configuration object.
        language: The programming language (python or go).
    """
    updated_version = get_current_version(language)
    success_msg = (
        f"\n{typer.style('✓', fg=typer.colors.GREEN, bold=True)} "
        f"Version bumped: {current_version_str} -> {updated_version}"
    )
    console.success(success_msg)

    # Show which files were actually modified
    files = _get_files_to_modify(config)
    if files:
        console.info(f"\n{typer.style('Modified files:', fg=typer.colors.CYAN, bold=True)}")
        for file_path in files:
            if file_path.exists():
                console.info(f"  • {file_path}")
    else:
        # Show common files that typically get modified
        console.info(f"\n{typer.style('Modified files:', fg=typer.colors.CYAN, bold=True)}")
        for file_path in [Path("pyproject.toml"), Path("VERSION"), Path("setup.py"), Path("setup.cfg")]:
            if file_path.exists():
                # Check if file was actually modified by checking content
                try:
                    content = file_path.read_text()
                    if updated_version in content:
                        console.info(f"  • {file_path}")
                except OSError:  # nosec B110 - safe to ignore file read errors  # noqa: S110
                    pass

    console.info("\nDon't forget to run 'uv lock' to update the lockfile if needed.")


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
    if not branch:
        return None

    # Get current branch
    result = run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False)
    if result.returncode != 0:
        return None

    current_branch = result.stdout.strip()
    if current_branch == branch:
        return None

    console.info(f"Switching from {current_branch} to {branch}")
    if not dry_run:
        result = run_git_command(["git", "checkout", branch], check=False)
        if result.returncode != 0:
            console.error(f"Failed to checkout branch {branch}: {result.stderr}")
            console.error(f"Ensure the branch '{branch}' exists: git branch -a")
            raise typer.Exit(code=1)
    else:
        console.info(f"[DRY-RUN] Would checkout branch {branch}")

    return current_branch


def _show_interactive_preview(
    current_version_str: str,
    new_version_str: str,
    current_git_branch: str,
) -> tuple[bool, bool, bool]:
    """Show interactive preview and prompt for commit/push decisions.

    In interactive mode, the user is asked step-by-step whether to proceed
    with the bump, whether to commit the changes, and whether to push.

    Args:
        current_version_str: Current version.
        new_version_str: New version.
        current_git_branch: Current git branch.

    Returns:
        Tuple of (proceed, commit, push). ``proceed`` is False if the user
        cancels the bump entirely.
    """
    import questionary as qs

    # Show preview
    console.info("\nPreview of changes:")
    console.info(f"  Version: {current_version_str} → {new_version_str}")
    console.info(f"  Branch: {current_git_branch}")

    # Confirm bump
    try:
        proceed = cast(bool, qs.confirm("Proceed with version bump?", default=True, style=COOL_STYLE).ask())
    except NON_INTERACTIVE_ERRORS:
        logger.debug("Running in non-interactive environment, proceeding automatically")
        proceed = True

    if not proceed:
        return False, False, False

    # Ask about commit
    try:
        commit = cast(bool, qs.confirm("Commit the changes?", default=True, style=COOL_STYLE).ask())
    except NON_INTERACTIVE_ERRORS:
        logger.debug("Running in non-interactive environment, committing automatically")
        commit = True

    # Ask about push (only if committing)
    push = False
    if commit:
        try:
            push = cast(bool, qs.confirm("Push changes to remote?", default=False, style=COOL_STYLE).ask())
        except NON_INTERACTIVE_ERRORS:
            logger.debug("Running in non-interactive environment, skipping push")
            push = False

    return True, commit, push


def _handle_push_to_remote(version: str | None) -> None:
    """Handle pushing changes to remote.

    Args:
        version: Version argument (None means interactive mode).

    Raises:
        typer.Exit: If push fails.
    """
    # Interactive prompt if not in non-interactive mode and version was not specified
    if not version:
        try:
            if not qs.confirm("Push changes to remote?", default=False, style=COOL_STYLE).ask():
                console.info("Push cancelled by user")
                return
        except NON_INTERACTIVE_ERRORS:
            # In testing or non-interactive environment, do not proceed with push
            console.info("Push cancelled - non-interactive environment detected")
            logger.debug("Running in non-interactive environment, skipping push")
            return

    console.info("Pushing changes to remote...")
    result = run_git_command(["git", "push"], check=False)
    if result.returncode == 0:
        console.success("Changes pushed to remote successfully!")
    else:
        console.error(f"Failed to push changes: {result.stderr}")
        console.error("The version bump has been applied locally but could not be pushed.")
        console.error("To recover:")
        console.error("  Push manually:   git push")
        console.error("  Or undo bump:    git reset --hard HEAD~1")
        raise typer.Exit(code=1)


def _restore_original_branch(original_branch: str | None, dry_run: bool) -> None:
    """Restore original branch if we switched.

    Args:
        original_branch: Original branch to restore, or None.
        dry_run: If True, don't actually restore (since we didn't actually switch).
    """
    if original_branch and not dry_run:
        console.info(f"Returning to original branch {original_branch}")
        run_git_command(["git", "checkout", original_branch], check=False)


def _resolve_bump_baseline(current_version_str: str) -> str:
    """Return the version to bump *from*, never lower than the latest remote tag.

    The local ``pyproject.toml`` can be stale (a branch that diverged before the
    previous release was merged), which historically caused relative bumps to
    generate already-released version numbers (issue #1126). When the highest
    semver tag on the remote is newer than the local version, that remote
    version is used as the baseline instead and the discrepancy is reported.

    The remote is queried best-effort: if it cannot be reached (offline, no
    remote configured) the local version is used unchanged.

    Args:
        current_version_str: The version read from the local project files.

    Returns:
        The version string to use as the basis for relative bumps.
    """
    latest_remote = get_latest_remote_version()
    if latest_remote is None:
        return current_version_str

    try:
        local_version = semver.Version.parse(current_version_str)
    except ValueError:
        local_version = None

    if local_version is None or latest_remote > local_version:
        console.warning(
            f"Local version {current_version_str} is behind the latest remote tag v{latest_remote}; "
            f"bumping from v{latest_remote} instead to avoid releasing an older version."
        )
        return str(latest_remote)

    return current_version_str


def _resolve_language(options: BumpOptions) -> Language:
    """Resolve the project language from options, auto-detecting when unset.

    Args:
        options: Configuration options for the bump command.

    Returns:
        The resolved programming language.

    Raises:
        typer.Exit: If no language is given and none can be detected.
    """
    if options.language is None:
        detected_language = Language.detect()
        if detected_language is None:
            console.error("Unable to detect project language.")
            console.error("Please specify language explicitly with --language option.")
            console.error("Supported languages: python, go")
            raise typer.Exit(code=1)
        language = detected_language
        console.info(f"Detected language: {typer.style(language.value, fg=typer.colors.CYAN, bold=True)}")
    else:
        language = options.language
        console.info(f"Using language: {typer.style(language.value, fg=typer.colors.CYAN, bold=True)}")
    return language


def _finalize_bump(
    options: BumpOptions,
    current_version_str: str,
    config: Any,
    language: Language,
    commit: bool,
    push: bool,
) -> None:
    """Report the outcome of a bump and push to remote when requested.

    In dry-run mode this only logs what would have happened; otherwise it logs
    the successful bump and, if ``push`` is set, pushes the changes to the remote.

    Args:
        options: Configuration options for the bump command.
        current_version_str: The original version string before the bump.
        config: The bumpversion configuration object.
        language: The programming language (python or go).
        commit: Whether the bump committed the change.
        push: Whether to push the change to the remote.
    """
    if options.dry_run:
        console.info("[DRY-RUN] Bump completed (no changes made)")
        if commit:
            console.info("[DRY-RUN] Would commit the changes")
        if push:
            console.info("[DRY-RUN] Would push changes to remote")
    else:
        _log_bump_success(current_version_str, config, language)

        # Handle push
        if push:
            _handle_push_to_remote(options.version)


def bump_command(options: BumpOptions) -> None:
    """Bump version using bump-my-version.

    This function handles the complete version bumping workflow including
    configuration loading, version parsing, interactive selection (if needed),
    and executing the bump operation.

    Supports multiple languages:
    - Python: uses pyproject.toml
    - Go: uses VERSION file with go.mod
    - Other: uses VERSION file

    Args:
        options: Configuration options for the bump command.

    Raises:
        typer.Exit: If project files are missing, configuration is invalid, or
            bump operation fails.

    Example:
        Bump to patch version::

            bump_command(BumpOptions(version="patch"))

        Bump with dry run::

            bump_command(BumpOptions(version="1.2.3", dry_run=True))

        Interactive bump with commit::

            bump_command(BumpOptions(commit=True))

        Bump and push to remote::

            bump_command(BumpOptions(version="minor", push=True))
    """
    # Detect or use provided language
    language = _resolve_language(options)

    _validate_project_exists(language)

    # Handle branch checkout if specified
    original_branch = _handle_branch_checkout(options.branch, options.dry_run)

    # Determine commit/push settings
    # In non-interactive mode (version specified), flags control behaviour directly.
    # In interactive mode (no version), the user is prompted for each step.
    is_interactive = not options.version
    commit = options.commit or options.push
    push = options.push

    current_version_str = get_current_version(language)
    config, config_path = _build_configuration(current_version_str, options.allow_dirty, commit, options.config)

    # Get current branch for display
    current_git_branch = get_current_git_branch()

    console.info(f"Current branch: {typer.style(current_git_branch, fg=typer.colors.CYAN, bold=True)}")
    console.info(f"Current version: {typer.style(current_version_str, fg=typer.colors.CYAN, bold=True)}")

    # Reconcile the bump baseline with the remote so a stale local pyproject.toml
    # (e.g. a branch that diverged before the previous release merged) cannot
    # produce a version lower than what is already published (issue #1126).
    # Explicit target versions are honoured as-is; only relative bumps
    # (patch/minor/major/prerelease) follow the remote-aware baseline.
    bump_baseline = _resolve_bump_baseline(current_version_str)

    # Determine new version string
    if options.version:
        new_version_str = _parse_version_argument(options.version, bump_baseline)
    else:
        new_version_str = get_interactive_bump_type(bump_baseline)

    console.info(f"New version will be: {typer.style(new_version_str, fg=typer.colors.GREEN, bold=True)}")

    # Show preview of file changes
    _preview_file_modifications(config, current_version_str, new_version_str)

    # Interactive preview and confirmation (only in true interactive mode)
    if is_interactive:
        proceed, commit, push = _show_interactive_preview(
            current_version_str,
            new_version_str,
            current_git_branch,
        )
        if not proceed:
            console.info("Version bump cancelled by user")
            raise typer.Exit(code=0)
        # Rebuild configuration with the user's commit decision
        config, config_path = _build_configuration(current_version_str, options.allow_dirty, commit, options.config)

    # Preflight: validate bump would succeed before making any changes
    if not options.dry_run:
        _preflight_bump(new_version_str, config, config_path)
        # Rebuild configuration to avoid stale state from dry-run
        config, config_path = _build_configuration(current_version_str, options.allow_dirty, commit, options.config)

    # When we are about to create a real commit, fold a freshly generated
    # CHANGELOG.md into it via git-cliff (mirroring how uv.lock is included). This
    # keeps the changelog current as part of the bump commit, avoiding a separate
    # unreviewed push to the default branch. No-op for projects without a cliff.toml.
    if commit and not options.dry_run:
        config.pre_commit_hooks = list(config.pre_commit_hooks) + _build_changelog_hooks(new_version_str)

    _execute_bump(new_version_str, config, config_path, options.dry_run)

    _finalize_bump(options, current_version_str, config, language, commit, push)

    # Restore original branch if we switched
    _restore_original_branch(original_branch, options.dry_run)
