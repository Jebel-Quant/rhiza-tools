"""Public data model for the rollback command.

Holds the ``RollbackOptions`` dataclass that carries the command's configuration.
Re-exported by ``rollback.py`` so the public import surface is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RollbackOptions:
    """Configuration options for the rollback command.

    Attributes:
        tag: The tag to rollback (e.g., "v1.2.3"). None for interactive selection.
        revert_bump: If True, also revert the version bump commit.
        dry_run: If True, show what would change without actually changing anything.
        non_interactive: If True, skip all confirmation prompts.
    """

    tag: str | None = None
    revert_bump: bool = False
    dry_run: bool = False
    non_interactive: bool = False
