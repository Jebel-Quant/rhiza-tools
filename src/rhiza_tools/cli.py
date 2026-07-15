"""CLI commands for Rhiza Tools.

This module defines the main Typer application and all command-line interface
commands for rhiza-tools. It provides the CI version matrix, benchmark
analysis, and dependency/suppression auditing.

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
from .commands.pip_audit import pip_audit_command
from .commands.suppression import suppression_audit_command
from .commands.version_matrix import version_matrix_command


def version_callback(value: bool) -> None:
    """Display the version and exit."""
    if value:
        typer.echo(f"rhiza-tools version {__version__}")
        raise typer.Exit()


app = typer.Typer(help="Rhiza Tools - Extra utilities for Rhiza.")

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
    """Rhiza Tools - Extra utilities for Rhiza."""
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
    candidates: Annotated[
        str | None,
        typer.Option(
            "--candidates",
            help="Comma-separated list of candidate Python versions (e.g., '3.11,3.12,3.13')",
        ),
    ] = None,
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Emit supported Python versions from pyproject.toml as JSON.

    This command reads the requires-python field from pyproject.toml and outputs
    a JSON array of Python versions that satisfy the constraint. This is primarily
    used in GitHub Actions to compute the test matrix. Each argument is documented
    by its ``--help`` text above.
    """
    _apply_verbose(verbose)
    candidates_list = None
    if candidates:
        candidates_list = [v.strip() for v in candidates.split(",")]

    version_matrix_command(pyproject_path=pyproject, candidates=candidates_list)


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


@app.command(
    name="pip-audit",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def pip_audit(ctx: typer.Context, verbose: bool = VERBOSE_OPTION) -> None:
    """Run pip-audit with a tiered vulnerability policy.

    Vulnerabilities in runtime dependencies fail the command; findings in build
    tooling (pip, setuptools, wheel, distribute) warn without failing. Any extra
    arguments after the command are forwarded verbatim to pip-audit
    (e.g. ``rhiza-tools pip-audit --ignore-vuln CVE-2024-1234``).
    """
    _apply_verbose(verbose)
    raise typer.Exit(code=pip_audit_command(ctx.args))


@app.command(
    name="suppression-audit",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def suppression_audit(
    ctx: typer.Context,
    fail_stale_nosec_cve: bool = typer.Option(
        False,
        "--fail-stale-nosec-cve",
        help="Fail when # nosec comments reference CVEs that pip-audit no longer reports.",
    ),
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Scan the codebase for inline suppressions and report a density grade.

    Detects inline suppression comments (# noqa, # nosec, # type: ignore,
    # pragma: no cover, # noinspection), and prints a per-file report, an ASCII
    histogram, and a letter grade. With ``--fail-stale-nosec-cve`` it also
    cross-checks CVE-tagged # nosec comments against live pip-audit findings and
    fails on stale ones; extra arguments are forwarded to pip-audit.
    """
    _apply_verbose(verbose)
    raise typer.Exit(code=suppression_audit_command(fail_stale_nosec_cve, ctx.args))
