"""CLI commands for Rhiza Tools.

This module defines the main Typer application for rhiza-tools. It currently
registers no subcommands (only the top-level ``--version`` option).

The CLI can be used either as a standalone tool (`rhiza-tools`) or as a
subcommand of the rhiza CLI (`rhiza tools`). See the project README for usage
examples.
"""

import typer

from rhiza_tools import __version__


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
