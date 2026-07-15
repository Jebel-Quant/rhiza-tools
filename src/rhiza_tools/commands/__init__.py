"""Commands for Rhiza Tools.

This package contains all command implementations for the rhiza-tools CLI.
Each command is implemented as a separate module with its own logic.

Available commands:
    - version_matrix_command: Python version matrix generation from pyproject.toml
    - analyze_benchmarks_command: Analyze and visualize pytest-benchmark results
    - release_command: Create and push release tags

The ``bump_command`` helper (in the :mod:`rhiza_tools.commands.bump` subpackage)
remains as an internal library used by :func:`release_command`; it is no longer
exposed as a standalone CLI command.

Example:
    Import and use commands::

        from rhiza_tools.commands import bump_command, version_matrix_command

        bump_command("patch")
        version_matrix_command()
"""

from .analyze_benchmarks import analyze_benchmarks_command
from .bump import bump_command
from .release import release_command
from .version_matrix import version_matrix_command

__all__ = [
    "analyze_benchmarks_command",
    "bump_command",
    "release_command",
    "version_matrix_command",
]
