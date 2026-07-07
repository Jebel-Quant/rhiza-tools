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

from pathlib import Path

import semver
import typer

from rhiza_tools import console
from rhiza_tools.commands._shared import (
    get_current_git_branch,
    get_latest_remote_version,
)

# Re-export the bump-my-version adapter helpers for the same reason. Names called
# directly inside this module (bump_command) need no alias; pure re-exports use one.
from rhiza_tools.commands.bump.engine import (
    BumpConfig,
    _build_changelog_hooks,
    _build_configuration,
    _execute_bump,
    _preflight_bump,
    _preview_file_modifications,
)
from rhiza_tools.commands.bump.engine import (
    _show_file_changes as _show_file_changes,
)

# Git helpers (branch checkout/restore, push to remote) live in bump/git.py; re-exported
# here so callers and tests that use ``rhiza_tools.commands.bump.<helper>`` keep working.
from rhiza_tools.commands.bump.git import (
    _handle_branch_checkout as _handle_branch_checkout,
)
from rhiza_tools.commands.bump.git import (
    _handle_push_to_remote as _handle_push_to_remote,
)
from rhiza_tools.commands.bump.git import (
    _restore_original_branch as _restore_original_branch,
)
from rhiza_tools.commands.bump.io import (
    SUPPORTED_LANGUAGES_MSG as SUPPORTED_LANGUAGES_MSG,
)

# Project I/O, interactive UI, and public data model live in bump/io.py; re-exported
# here so callers and tests that use ``rhiza_tools.commands.bump.<name>`` keep working.
from rhiza_tools.commands.bump.io import (
    BumpOptions as BumpOptions,
)
from rhiza_tools.commands.bump.io import (
    Language as Language,
)
from rhiza_tools.commands.bump.io import (
    _log_bump_success as _log_bump_success,
)
from rhiza_tools.commands.bump.io import (
    _show_interactive_preview as _show_interactive_preview,
)
from rhiza_tools.commands.bump.io import (
    _validate_project_exists as _validate_project_exists,
)
from rhiza_tools.commands.bump.io import (
    get_current_version as get_current_version,
)
from rhiza_tools.commands.bump.io import (
    get_interactive_bump_type as get_interactive_bump_type,
)
from rhiza_tools.commands.bump.io import (
    parse_language_option as parse_language_option,
)

# Re-export pure version-math helpers so external callers and tests that reference
# ``rhiza_tools.commands.bump.<name>`` (including monkeypatch string paths) keep
# working after these moved to bump/versioning.py. The redundant ``as`` aliases mark
# them as intentional re-exports for ruff (F401).
from rhiza_tools.commands.bump.versioning import (
    _CHOICE_PREFIX_TO_BUMP_TYPE as _CHOICE_PREFIX_TO_BUMP_TYPE,
)
from rhiza_tools.commands.bump.versioning import (
    _VALID_BUMP_TYPES as _VALID_BUMP_TYPES,
)
from rhiza_tools.commands.bump.versioning import (
    _denormalize_pep440_to_semver as _denormalize_pep440_to_semver,
)
from rhiza_tools.commands.bump.versioning import (
    _determine_bump_type_from_choice as _determine_bump_type_from_choice,
)
from rhiza_tools.commands.bump.versioning import (
    _parse_version_argument,
)
from rhiza_tools.commands.bump.versioning import (
    _validate_explicit_version as _validate_explicit_version,
)
from rhiza_tools.commands.bump.versioning import (
    get_bumped_version_from_type as get_bumped_version_from_type,
)
from rhiza_tools.commands.bump.versioning import (
    get_next_prerelease as get_next_prerelease,
)


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
            console.error(SUPPORTED_LANGUAGES_MSG)
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
    config: BumpConfig,
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


def _resolve_new_version(options: BumpOptions, bump_baseline: str) -> str:
    """Resolve the target version string.

    Explicit target versions are honoured as-is; otherwise the user is prompted
    interactively for the bump type relative to ``bump_baseline``.

    Args:
        options: Configuration options for the bump command.
        bump_baseline: The version to bump from (remote-aware baseline).

    Returns:
        The new version string.
    """
    if options.version:
        return _parse_version_argument(options.version, bump_baseline)
    return get_interactive_bump_type(bump_baseline)


def _confirm_interactive_bump(
    options: BumpOptions,
    current_version_str: str,
    new_version_str: str,
    current_git_branch: str,
) -> tuple[BumpConfig, Path, bool, bool]:
    """Show the interactive preview and rebuild config from the user's choices.

    Args:
        options: Configuration options for the bump command.
        current_version_str: The current version string.
        new_version_str: The resolved target version string.
        current_git_branch: The current git branch, for display.

    Returns:
        Tuple of (config, config_path, commit, push) reflecting the user's
        commit/push decisions.

    Raises:
        typer.Exit: If the user cancels the bump.
    """
    proceed, commit, push = _show_interactive_preview(current_version_str, new_version_str, current_git_branch)
    if not proceed:
        console.info("Version bump cancelled by user")
        raise typer.Exit(code=0)
    # Rebuild configuration with the user's commit decision.
    config, config_path = _build_configuration(current_version_str, options.allow_dirty, commit, options.config)
    return config, config_path, commit, push


def _prepare_config_for_execution(
    options: BumpOptions,
    current_version_str: str,
    new_version_str: str,
    config: BumpConfig,
    config_path: Path,
    commit: bool,
) -> tuple[BumpConfig, Path]:
    """Run preflight validation and fold in changelog hooks before executing.

    In dry-run mode this is a no-op. Otherwise it validates that the bump would
    succeed, rebuilds a clean config to avoid stale dry-run state, and — when a
    real commit will be made — appends the git-cliff changelog hooks.

    Args:
        options: Configuration options for the bump command.
        current_version_str: The current version string.
        new_version_str: The resolved target version string.
        config: The current bumpversion configuration.
        config_path: Path to the generated bumpversion config.
        commit: Whether the bump will commit the change.

    Returns:
        The (config, config_path) to execute the bump with.
    """
    if options.dry_run:
        return config, config_path

    # Preflight: validate bump would succeed before making any changes.
    _preflight_bump(new_version_str, config, config_path)
    # Rebuild configuration to avoid stale state from the dry-run preflight.
    config, config_path = _build_configuration(current_version_str, options.allow_dirty, commit, options.config)

    # When we are about to create a real commit, fold a freshly generated
    # CHANGELOG.md into it via git-cliff (mirroring how uv.lock is included). This
    # keeps the changelog current as part of the bump commit, avoiding a separate
    # unreviewed push to the default branch. No-op for projects without a cliff.toml.
    if commit:
        config.pre_commit_hooks = list(config.pre_commit_hooks) + _build_changelog_hooks(new_version_str)

    return config, config_path


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
    new_version_str = _resolve_new_version(options, bump_baseline)

    console.info(f"New version will be: {typer.style(new_version_str, fg=typer.colors.GREEN, bold=True)}")

    # Show preview of file changes
    _preview_file_modifications(config, current_version_str, new_version_str)

    # Interactive preview and confirmation (only in true interactive mode)
    if is_interactive:
        config, config_path, commit, push = _confirm_interactive_bump(
            options, current_version_str, new_version_str, current_git_branch
        )

    config, config_path = _prepare_config_for_execution(
        options, current_version_str, new_version_str, config, config_path, commit
    )

    _execute_bump(new_version_str, config, config_path, options.dry_run)

    _finalize_bump(options, current_version_str, config, language, commit, push)

    # Restore original branch if we switched
    _restore_original_branch(original_branch, options.dry_run)
