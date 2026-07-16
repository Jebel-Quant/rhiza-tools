"""Commands for Rhiza Tools.

This package contains all command implementations for the rhiza-tools CLI.
Each command is implemented as a separate module with its own logic.

Available commands:
    - version_matrix_command: Python version matrix generation from pyproject.toml

Example:
    Import and use commands::

        from rhiza_tools.commands import version_matrix_command

        version_matrix_command()
"""

from .version_matrix import version_matrix_command

__all__ = [
    "version_matrix_command",
]
