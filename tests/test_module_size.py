"""Module-size gate keeping command modules small enough to navigate.

Issue #207 split the oversized ``bump.py`` into focused modules, and #223 gave
``release.py`` (-> ``release_versioning.py``) and ``rollback.py`` (->
``rollback_git.py``) the same treatment. Issue #237 completed the split by
extracting ``bump_io``, ``bump_git``, ``release_git``, and ``rollback_io``,
bringing every command module below 500 lines. This gate prevents regression:
every command module must stay at or below a 500-line ceiling, so future growth
is split out rather than accreted into one file.
"""

from __future__ import annotations

from pathlib import Path

_MAX_LINES = 500
_COMMANDS_DIR = Path(__file__).resolve().parent.parent / "src" / "rhiza_tools" / "commands"


def test_command_modules_within_size_limit():
    """Every ``src/rhiza_tools/commands/*.py`` must be at most 800 lines."""
    offenders: dict[str, int] = {}
    for module_path in sorted(_COMMANDS_DIR.glob("*.py")):
        line_count = len(module_path.read_text(encoding="utf-8").splitlines())
        if line_count > _MAX_LINES:
            offenders[module_path.name] = line_count

    assert not offenders, (
        f"command modules exceed the {_MAX_LINES}-line limit: {offenders}. "
        "Split cohesive responsibilities into a new module."
    )
