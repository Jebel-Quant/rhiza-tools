"""CLI commands for Rhiza Tools.

This module defines the main Typer application and all command-line interface
commands for rhiza-tools. It provides commands for version bumping, release
management, and the CI version matrix.

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
from .commands.bump import BumpOptions, bump_command, parse_language_option
from .commands.pip_audit import pip_audit_command
from .commands.release import release_command
from .commands.rollback import RollbackOptions, rollback_command
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
CONFIG_OPTION = typer.Option(
    None,
    "--config",
    "-c",
    help="Path to the .cfg.toml bumpversion config file. Defaults to .rhiza/.cfg.toml.",
)


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


@app.command()
def bump(
    version: str | None = typer.Argument(None, help="The version to bump to (e.g., 1.0.1, major, minor, patch, etc)"),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Programming language (python or go). Auto-detected if not specified."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
    commit: bool = typer.Option(False, "--commit", help="Commit the changes to git."),
    push: bool = typer.Option(False, "--push", help="Push changes to remote after commit (implies --commit)."),
    branch: str | None = typer.Option(
        None, "--branch", help="Branch to perform the bump on (default: current branch)."
    ),
    allow_dirty: bool = typer.Option(
        False, "--allow-dirty", help="Allow bumping even if the working directory is dirty."
    ),
    config: Path | None = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Bump the version of the project.

    This command updates the version for Python (pyproject.toml) or Go (VERSION file)
    projects using semantic versioning. You can provide an explicit version number,
    a bump type (patch, minor, major), or leave it blank for an interactive prompt.

    Each argument is documented by its ``--help`` text above; see
    :func:`rhiza_tools.commands.bump.bump_command` for the underlying behaviour.
    """
    _apply_verbose(verbose)
    lang_enum = parse_language_option(language)

    options = BumpOptions(
        version=version,
        dry_run=dry_run,
        commit=commit,
        push=push,
        branch=branch,
        allow_dirty=allow_dirty,
        language=lang_enum,
        config=config,
    )
    bump_command(options)


@app.command()
def release(
    bump: str | None = typer.Option(
        None, "--bump", help="Bump type (MAJOR, MINOR, PATCH). Selected interactively when omitted."
    ),
    push: bool = typer.Option(False, "--push", help="Push changes to remote (default: prompt in interactive mode)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
    non_interactive: bool = typer.Option(False, "--non-interactive", "-y", help="Skip all confirmation prompts."),
    language: str | None = typer.Option(
        None, "--language", "-l", help="Programming language (python or go). Auto-detected if not specified."
    ),
    allow_older: bool = typer.Option(
        False,
        "--allow-older",
        help="Allow releasing a version not newer than the latest remote release (maintenance/back-branch).",
    ),
    config: Path | None = CONFIG_OPTION,
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Bump the version and push a release tag to remote to trigger the release workflow.

    A release always bumps the version before tagging: the bump type is taken
    from ``--bump`` when given, selected interactively otherwise, or defaults to
    patch in non-interactive mode. The command then validates the repository
    state and pushes the git tag, which triggers the automated release workflow.
    Supports Python projects (pyproject.toml) and Go projects (go.mod + VERSION
    file). The project language is auto-detected when not explicitly specified.

    Each argument is documented by its ``--help`` text above; see
    :func:`rhiza_tools.commands.release.release_command` for the underlying behaviour.
    """
    _apply_verbose(verbose)
    lang_enum = parse_language_option(language)

    release_command(bump, push, dry_run, non_interactive, lang_enum, config, allow_older)


@app.command()
def rollback(
    tag: str | None = typer.Argument(None, help="Tag to rollback (e.g., v1.2.3). Interactive if omitted."),
    revert_bump: bool = typer.Option(False, "--revert-bump", help="Also revert the version bump commit."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
    non_interactive: bool = typer.Option(False, "--non-interactive", "-y", help="Skip all confirmation prompts."),
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Rollback a release and/or version bump.

    This command safely reverses release and bump operations by deleting
    the release tag from local and remote repositories, and optionally
    reverting the version bump commit.

    It uses ``git revert`` rather than ``git reset``, making it safe
    even when changes have already been pushed to remote.

    Each argument is documented by its ``--help`` text above; see
    :func:`rhiza_tools.commands.rollback.rollback_command` for the underlying behaviour.
    """
    _apply_verbose(verbose)
    options = RollbackOptions(
        tag=tag,
        revert_bump=revert_bump,
        dry_run=dry_run,
        non_interactive=non_interactive,
    )
    rollback_command(options)


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
