"""CLI commands for Rhiza Tools.

This module defines the main Typer application and all command-line interface
commands for rhiza-tools. It provides the CI Python-version matrix.

The CLI can be used either as a standalone tool (`rhiza-tools`) or as a
subcommand of the rhiza CLI (`rhiza tools`). See the project README for usage
examples.
"""

from pathlib import Path
from typing import Annotated

import typer

from rhiza_tools import __version__

from .commands.version_matrix import version_matrix_command


def version_callback(value: bool) -> None:
    """Display the version and exit."""
    if value:
        typer.echo(f"rhiza-tools version {__version__}")
        raise typer.Exit()


app = typer.Typer(help="Rhiza Tools — CI helper CLI for the Rhiza ecosystem.")


@app.callback()
def main(
    version: bool = typer.Option(  # eager option; value is consumed by version_callback, not the body
        None,
        "--version",
        help="Show the version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Rhiza Tools — CI helper CLI for the Rhiza ecosystem."""


@app.command(name="version-matrix")
def version_matrix(
    pyproject: Annotated[
        Path,
        typer.Option(
            "--pyproject",
            help="Path to pyproject.toml file",
        ),
    ] = Path("pyproject.toml"),
) -> None:
    """Emit supported Python versions from pyproject.toml as JSON.

    This command reads the ``Programming Language :: Python :: X.Y`` trove
    classifiers from pyproject.toml and outputs a JSON array of those versions.
    This is primarily used in GitHub Actions to compute the test matrix. Each
    argument is documented by its ``--help`` text above.
    """
    version_matrix_command(pyproject_path=pyproject)
