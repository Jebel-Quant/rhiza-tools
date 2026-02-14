"""Commands for Rhiza Tools.

This package contains all command implementations for the rhiza-tools CLI.
Each command is implemented as a separate module with its own logic.

Available commands:
    - bump_command: Version bumping with semantic versioning support
    - update_readme_command: README synchronization with make help output
    - generate_coverage_badge_command: Coverage badge generation
    - version_matrix_command: Python version matrix generation from pyproject.toml
    - analyze_benchmarks_command: Analyze and visualize pytest-benchmark results
    - release_command: Create and push release tags
    - recover_command: Recover (rollback) a release and/or version bump

Example:
    Import and use commands::

        from rhiza_tools.commands import bump_command, update_readme_command, version_matrix_command

        bump_command("patch")
        update_readme_command()
        version_matrix_command()
"""

from .analyze_benchmarks import analyze_benchmarks_command
from .bump import bump_command
from .recover import recover_command
from .release import release_command
from .update_readme import update_readme_command
from .version_matrix import version_matrix_command

__all__ = [
    "analyze_benchmarks_command",
    "bump_command",
    "recover_command",
    "release_command",
    "update_readme_command",
    "version_matrix_command",
]
