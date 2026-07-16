"""CLI commands for Rhiza Tools.

This module defines the main Typer application and all command-line interface
commands for rhiza-tools. It provides the CI Python-version matrix and
benchmark analysis.

The CLI can be used either as a standalone tool (`rhiza-tools`) or as a
subcommand of the rhiza CLI (`rhiza tools`). See the project README for usage
examples.
"""

from pathlib import Path
from typing import Annotated

import typer

from rhiza_tools import __version__
from rhiza_tools.console import configure as configure_console

from .commands.analyze_benchmarks import analyze_benchmarks_command
from .commands.version_matrix import version_matrix_command


def version_callback(value: bool) -> None:
    """Display the version and exit."""
    if value:
        typer.echo(f"rhiza-tools version {__version__}")
        raise typer.Exit()


app = typer.Typer(help="Rhiza Tools — CI helper CLI for the Rhiza ecosystem.")

# Shared option so --verbose / -v works both before and after the subcommand.
VERBOSE_OPTION = typer.Option(False, "--verbose", "-v", help="Show verbose debug output.")


def _apply_verbose(verbose: bool) -> None:
    """Enable verbose output if the flag was passed on the subcommand."""
    if verbose:
        configure_console(verbose=True)


@app.callback()
def main(
    version: bool = typer.Option(  # noqa: ARG001 — eager option; value is consumed by version_callback, not the body
        None,
        "--version",
        help="Show the version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Rhiza Tools — CI helper CLI for the Rhiza ecosystem."""
    configure_console(verbose=verbose)


@app.command(name="version-matrix")
def version_matrix(
    pyproject: Annotated[
        Path,
        typer.Option(
            "--pyproject",
            help="Path to pyproject.toml file",
        ),
    ] = Path("pyproject.toml"),
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Emit supported Python versions from pyproject.toml as JSON.

    This command reads the ``Programming Language :: Python :: X.Y`` trove
    classifiers from pyproject.toml and outputs a JSON array of those versions.
    This is primarily used in GitHub Actions to compute the test matrix. Each
    argument is documented by its ``--help`` text above.
    """
    _apply_verbose(verbose)
    version_matrix_command(pyproject_path=pyproject)


@app.command(name="analyze-benchmarks")
def analyze_benchmarks(
    benchmarks_json: Annotated[
        Path,
        typer.Option(
            "--benchmarks-json",
            help="Path to benchmarks.json file",
        ),
    ] = Path("_benchmarks/benchmarks.json"),
    output_html: Annotated[
        Path,
        typer.Option(
            "--output-html",
            help="Path to save HTML visualization",
        ),
    ] = Path("_benchmarks/benchmarks.html"),
    show: Annotated[
        bool,
        typer.Option(
            "--show/--no-show",
            help="Open the interactive chart in a browser after saving (default: no-show)",
        ),
    ] = False,
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Analyze pytest-benchmark results and visualize them.

    This command reads a benchmarks.json file produced by pytest-benchmark,
    prints a table with benchmark name, mean milliseconds, and operations per
    second, and generates an interactive Plotly bar chart of mean runtimes.

    Note: This command requires pandas and plotly. Install with:
    uv pip install -e '.[dev]' or pip install 'rhiza-tools[dev]'

    Each argument is documented by its ``--help`` text above.
    """
    _apply_verbose(verbose)
    analyze_benchmarks_command(benchmarks_json=benchmarks_json, output_html=output_html, show=show)
