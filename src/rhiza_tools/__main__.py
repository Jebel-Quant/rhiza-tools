"""Rhiza tools module entry point.

This module serves as the entry point for the Rhiza Tools command-line interface (CLI).
When the package is executed as a script (python -m rhiza_tools), it starts the Typer
application defined in rhiza_tools.cli.

Example:
    Run as a module::

        $ python -m rhiza_tools version-matrix
        $ python -m rhiza_tools --help

    Or use the installed entry point::

        $ rhiza-tools version-matrix
        $ rhiza-tools --help
"""

from rhiza_tools.cli import app

if __name__ == "__main__":
    app()
