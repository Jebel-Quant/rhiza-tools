"""Post-bump reporting helpers for the bump command.

This module holds the helpers that report a completed bump to the user: listing
the files that were modified (``_log_modified_files``,
``_log_conventional_version_files``) and printing the success summary with
follow-up instructions (``_log_bump_success``).

All public symbols defined here are re-exported by ``bump/__init__.py`` so the
public import surface is unchanged.
"""

from __future__ import annotations

from pathlib import Path

import typer

from rhiza_tools import console
from rhiza_tools.commands.bump.engine import BumpConfig, _get_files_to_modify
from rhiza_tools.commands.bump.io import get_current_version
from rhiza_tools.commands.bump.models import Language


def _log_conventional_version_files(updated_version: str) -> None:
    """List conventional version-bearing files whose contents include the new version.

    Used as a fallback when the config declares no explicit files to modify.

    Args:
        updated_version: The version string after the bump.
    """
    for file_path in [Path("pyproject.toml"), Path("VERSION"), Path("setup.py"), Path("setup.cfg")]:
        if file_path.exists():
            # Check if file was actually modified by checking content
            try:
                content = file_path.read_text()
                if updated_version in content:
                    console.info(f"  • {file_path}")
            except Exception:  # nosec B110 - safe to ignore file read errors  # noqa: S110, BLE001
                pass


def _log_modified_files(config: BumpConfig, updated_version: str) -> None:
    """Print the files that the bump modified.

    When the config declares files to modify, list those that exist. Otherwise
    fall back to the files that conventionally carry a version, reporting only
    the ones whose contents now include ``updated_version``.

    Args:
        config: The bumpversion configuration object.
        updated_version: The version string after the bump.
    """
    console.info(f"\n{typer.style('Modified files:', fg=typer.colors.CYAN, bold=True)}")

    files = _get_files_to_modify(config)
    if files:
        for file_path in files:
            if file_path.exists():
                console.info(f"  • {file_path}")
        return

    _log_conventional_version_files(updated_version)


def _log_bump_success(current_version_str: str, config: BumpConfig, language: Language) -> None:
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

    _log_modified_files(config, updated_version)

    console.info("\nDon't forget to run 'uv lock' to update the lockfile if needed.")
