"""Adapter isolating all bump-my-version integration for the bump command.

This module is the single place in rhiza-tools that touches bump-my-version
internals (``bumpversion.bump.do_bump``, ``bumpversion.config.get_configuration``,
``bumpversion.ui.setup_logging`` and the shape of the configuration object). All
other modules go through the helpers defined here, so an upstream change in
bump-my-version only has to be reconciled in one location. The companion
contract test in ``tests/test_bumpversion_contract.py`` pins the upstream
interface this adapter relies on.
"""

from pathlib import Path
from typing import TypeAlias

import typer
from bumpversion.bump import do_bump
from bumpversion.config import get_configuration
from bumpversion.config.models import Config
from bumpversion.exceptions import BumpVersionError
from bumpversion.ui import setup_logging
from loguru import logger

from rhiza_tools import console
from rhiza_tools.config import CONFIG_FILENAME

# ``BumpConfig`` is bump-my-version's concrete ``bumpversion.config.models.Config``.
# It is used directly (rather than ``Any`` or a structural Protocol) because
# ``do_bump`` requires this exact type, so the adapter must hold a real ``Config``
# anyway. Importing it keeps every helper below fully typed under strict ``ty``.
# The companion ``tests/test_bumpversion_contract.py`` pins the attributes used.
#
# Declared as an explicit ``TypeAlias`` (not ``import ... as BumpConfig``) so it
# is (a) a re-export the split bump command modules can import under mypy
# ``--strict``'s no-implicit-reexport rule, and (b) usable in annotations even
# though bump-my-version is untyped (``Config`` resolves to ``Any``).
BumpConfig: TypeAlias = Config


def _build_configuration(
    current_version_str: str,
    allow_dirty: bool,
    commit: bool,
    config_path: Path | None = None,
) -> tuple[BumpConfig, Path]:
    """Build bumpversion configuration with appropriate overrides.

    Args:
        current_version_str: The current version string.
        allow_dirty: If True, allow bumping even with uncommitted changes.
        commit: If True, automatically commit the version change to git.
        config_path: Path to the .cfg.toml config file. Defaults to CONFIG_FILENAME.

    Returns:
        A tuple of (config object, config_path).

    Raises:
        typer.Exit: If configuration loading fails.
    """
    if config_path is None:
        config_path = Path(CONFIG_FILENAME)
    overrides: dict[str, str | bool] = {"current_version": current_version_str}
    if allow_dirty:
        overrides["allow_dirty"] = True
    if commit:
        overrides["commit"] = True

    try:
        config = get_configuration(config_file=config_path, **overrides)
    # Config loading fails in a few distinct ways: a malformed TOML file raises
    # tomlkit's ``ParseError`` (a ``ValueError``), bump-my-version validation
    # raises ``BumpVersionError``, and an unreadable file raises ``OSError``.
    except (BumpVersionError, ValueError, OSError) as e:
        console.error(f"Failed to load bumpversion configuration: {e}")
        console.error(f"Check your bumpversion config at: {config_path}")
        console.error("Ensure the [tool.bumpversion] section is valid TOML with correct version patterns.")
        raise typer.Exit(code=1) from None
    else:
        return config, config_path


def _build_changelog_hooks(new_version: str) -> list[str]:
    """Build git-cliff pre-commit hooks that fold CHANGELOG.md into the bump commit.

    bump-my-version commits whatever is staged when it runs its ``pre_commit_hooks`` —
    the same mechanism the project config already uses to include ``uv.lock``.
    Regenerating the changelog there means the version bump, the lockfile and the
    changelog land in a single commit and tag, with no separate push to the default
    branch. That separate push is undesirable: it is blocked by branch-protection
    rulesets and counts as an unreviewed change against the OpenSSF Scorecard
    Code-Review check.

    The hooks are only emitted when the project is configured for git-cliff (a
    ``cliff.toml`` is present), so projects without changelog tooling are unaffected.
    The new version is passed with ``--tag`` because the release tag does not exist
    yet when the hooks run; otherwise git-cliff would file the new entries under
    "unreleased".

    Args:
        new_version: The version being bumped to (without a leading ``v``).

    Returns:
        The git-cliff hook commands, or an empty list when git-cliff is not configured.

    Example:
        >>> _build_changelog_hooks("1.2.3")  # doctest: +SKIP
        ['uvx git-cliff --tag v1.2.3 --output CHANGELOG.md', 'git add CHANGELOG.md']
    """
    if not (Path("cliff.toml").exists() or Path(".cliff.toml").exists()):
        return []
    return [
        f"uvx git-cliff --tag v{new_version} --output CHANGELOG.md",
        "git add CHANGELOG.md",
    ]


def _get_files_to_modify(config: BumpConfig) -> list[Path]:
    """Get list of files that will be modified by bump-my-version.

    Args:
        config: The bumpversion configuration object.

    Returns:
        List of file paths that will be modified.
    """
    files = []
    if hasattr(config, "files_to_modify"):
        for file_config in config.files_to_modify:
            # ``filename`` is typed ``str | None`` upstream; skip unnamed entries.
            filename = file_config.filename
            if filename:
                files.append(Path(filename))
    return files


def _show_file_changes(file_path: Path, current_version: str, new_version: str) -> None:
    """Show the changes that will be made to a file.

    Args:
        file_path: Path to the file to preview.
        current_version: The current version string.
        new_version: The new version string.
    """
    if not file_path.exists():
        console.warning(f"File not found: {file_path}")
        return

    try:
        content = file_path.read_text()
        lines_with_version = []

        for i, line in enumerate(content.split("\n"), 1):
            if current_version in line:
                lines_with_version.append((i, line))

        if lines_with_version:
            console.info(f"  Changes in {typer.style(str(file_path), fg=typer.colors.CYAN, bold=True)}:")
            for line_num, old_line in lines_with_version:
                new_line = old_line.replace(current_version, new_version)
                console.info(f"    Line {line_num}:")
                console.info(f"      {typer.style('-', fg=typer.colors.RED)} {old_line.strip()}")
                console.info(f"      {typer.style('+', fg=typer.colors.GREEN)} {new_line.strip()}")
    except OSError as e:
        # Previewing is best-effort; an unreadable file should not abort the bump.
        logger.debug(f"Could not preview changes for {file_path}: {e}")


def _preview_file_modifications(config: BumpConfig, current_version: str, new_version: str) -> None:
    """Preview what changes will be made to files.

    Args:
        config: The bumpversion configuration object.
        current_version: The current version string.
        new_version: The new version string.
    """
    files = _get_files_to_modify(config)

    if files:
        console.info(f"\n{typer.style('Files to be modified:', fg=typer.colors.YELLOW, bold=True)}")
        for file_path in files:
            _show_file_changes(file_path, current_version, new_version)
        console.info("")  # Empty line for spacing
    else:
        # Fallback: check common files
        common_files = [Path("pyproject.toml"), Path("VERSION"), Path("setup.py"), Path("setup.cfg")]
        console.info(f"\n{typer.style('Files to be modified:', fg=typer.colors.YELLOW, bold=True)}")
        for file_path in common_files:
            if file_path.exists():
                _show_file_changes(file_path, current_version, new_version)
        console.info("")  # Empty line for spacing


def _preflight_bump(new_version_str: str, config: BumpConfig, config_path: Path) -> None:
    """Run a dry-run bump to validate the operation would succeed.

    This preflight check ensures the bump operation will succeed before making
    any actual changes. It catches configuration errors, file access issues,
    and version format problems early, preventing partial failures that would
    leave the repository in a state requiring manual recovery.

    Args:
        new_version_str: The new version string to validate.
        config: The bumpversion configuration object.
        config_path: Path to the bumpversion configuration file.

    Raises:
        typer.Exit: If the preflight validation fails.
    """
    console.info("Running preflight validation (dry-run)...")
    setup_logging(verbose=1 if console.is_verbose() else 0)

    try:
        do_bump(
            version_part=None,
            new_version=new_version_str,
            config=config,
            config_file=config_path,
            dry_run=True,
        )
    # do_bump surfaces version/format/hook problems as ``BumpVersionError`` and
    # file-access problems as ``OSError``; both mean the bump cannot proceed.
    except (BumpVersionError, OSError) as e:
        console.error(f"Preflight validation failed: {e}")
        console.error("No changes were made.")
        raise typer.Exit(code=1) from None

    console.success("Preflight validation passed")


def _execute_bump(new_version_str: str, config: BumpConfig, config_path: Path, dry_run: bool) -> None:
    """Execute the bump operation using bump-my-version.

    Args:
        new_version_str: The new version string to bump to.
        config: The bumpversion configuration object.
        config_path: Path to the bumpversion configuration file.
        dry_run: If True, show what would change without actually changing anything.

    Raises:
        typer.Exit: If the bump operation fails.
    """
    console.info("Running bump-my-version...")
    setup_logging(verbose=1 if console.is_verbose() else 0)

    try:
        do_bump(
            version_part=None,
            new_version=new_version_str,
            config=config,
            config_file=config_path,
            dry_run=dry_run,
        )
    # do_bump surfaces version/format/hook problems as ``BumpVersionError`` and
    # file-access problems as ``OSError``; both can leave files partially edited.
    except (BumpVersionError, OSError) as e:
        console.error(f"bump-my-version failed: {e}")
        if not dry_run:
            console.error("Files may have been partially modified. To recover:")
            console.error("  1. Check modified files: git diff")
            console.error("  2. Restore all changes:  git checkout -- .")
            console.error("  3. Remove untracked:     git clean -fd")
            console.error("Or to keep changes, fix the issue and retry.")
        raise typer.Exit(code=1) from None
