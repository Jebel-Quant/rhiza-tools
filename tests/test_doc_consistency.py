"""Consistency gate between the CLI commands and the README documentation.

Every command registered on the Typer app must be documented in README.md, and
every command documented there must exist. This keeps the docs from silently
drifting as commands are added, removed or renamed.
"""

from __future__ import annotations

import re
from pathlib import Path

from rhiza_tools.cli import app

README = Path(__file__).resolve().parent.parent / "README.md"


def _normalize(name: str) -> str:
    """Normalize a command name for comparison (Typer maps underscores to hyphens)."""
    return name.replace("_", "-")


def _registered_command_names() -> set[str]:
    """Return the normalized names of every command registered on the Typer app."""
    names: set[str] = set()
    for command in app.registered_commands:
        raw = command.name or (command.callback.__name__ if command.callback else None)
        assert raw, "every registered command must resolve to a name"
        names.add(_normalize(raw))
    return names


def _documented_command_names() -> set[str]:
    """Return command names documented as ``### `name` `` headers in the Commands section."""
    text = README.read_text(encoding="utf-8")
    # Restrict to the "## Commands" section so unrelated headers are not matched.
    commands_section = text.split("## Commands", 1)[-1].split("\n## ", 1)[0]
    return {_normalize(m) for m in re.findall(r"^### `([^`]+)`", commands_section, flags=re.MULTILINE)}


def test_every_command_is_documented():
    """Each registered CLI command must appear as a documented section in the README."""
    missing = _registered_command_names() - _documented_command_names()
    assert not missing, f"commands missing from the README Commands section: {sorted(missing)}"


def test_every_documented_command_exists():
    """Each command documented in the README must be a real registered command."""
    stale = _documented_command_names() - _registered_command_names()
    assert not stale, f"README documents non-existent commands: {sorted(stale)}"
