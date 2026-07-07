"""CLI commands for Rhiza Tools.

This module defines the main Typer application and all command-line interface
commands for rhiza-tools. It provides commands for version bumping, coverage
badge generation, release management, and README updates.

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
from .commands.bump import bump_command
from .commands.generate_badge import generate_coverage_badge_command
from .commands.release import release_command
from .commands.rollback import rollback_command
from .commands.update_readme import update_readme_command
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

    Args:
        version: The version to bump to. Can be an explicit version (e.g., "1.2.3"),
            a bump type ("patch", "minor", "major"), a prerelease type
            ("alpha", "beta", "rc", "dev"), or None for interactive selection.
        language: Programming language (python or go). Auto-detected if not specified.
        dry_run: If True, show what would change without actually changing anything.
        commit: If True, automatically commit the version change to git.
        push: If True, push changes to remote after commit (implies --commit).
        branch: Branch to perform the bump on (default: current branch).
        allow_dirty: If True, allow bumping even with uncommitted changes.
        config: Path to the .cfg.toml bumpversion config file. Defaults to .rhiza/.cfg.toml.
        verbose: If True, enable verbose debug output.
    """
    _apply_verbose(verbose)
    from rhiza_tools.commands.bump import BumpOptions, parse_language_option

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
def generate_coverage_badge(
    coverage_json: Annotated[
        Path,
        typer.Option(
            "--coverage-json",
            help="Path to coverage.json file",
        ),
    ] = Path("_tests/coverage.json"),
    output: Annotated[
        Path,
        typer.Option(
            help="Path to output badge JSON",
        ),
    ] = Path("_book/tests/coverage-badge.json"),
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Generate a coverage badge for the project.

    Reads a coverage report JSON file and creates a shields.io endpoint JSON file
    for displaying a coverage badge. The badge color automatically adjusts based
    on the coverage percentage.

    Args:
        coverage_json: Path to the coverage.json file generated by pytest-cov.
        output: Path where the badge JSON file should be written.
        verbose: If True, enable verbose debug output.
    """
    _apply_verbose(verbose)
    generate_coverage_badge_command(coverage_json_path=coverage_json, output_path=output)


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

    Args:
        bump: Bump type (MAJOR, MINOR, PATCH) to apply. Selected interactively when omitted.
        push: If True, push changes without prompting (implies non-interactive for push).
        dry_run: If True, show what would happen without actually pushing the tag.
        non_interactive: If True, skip all confirmation prompts and default the bump to
            patch when no --bump type is given (useful for CI/CD).
        language: Programming language (python or go). Auto-detected if not specified.
        allow_older: If True, allow releasing a version not newer than the latest remote release.
        config: Path to the .cfg.toml bumpversion config file. Passed through to the bump.
        verbose: If True, enable verbose debug output.
    """
    _apply_verbose(verbose)
    from rhiza_tools.commands.bump import parse_language_option

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

    Args:
        tag: The tag to rollback (e.g., "v1.2.3"). If omitted, an interactive
            menu shows recent tags to choose from.
        revert_bump: If True, also revert the version bump commit associated
            with the tag.
        dry_run: If True, show what would happen without actually making changes.
        non_interactive: If True, skip all confirmation prompts (useful for CI/CD).
        verbose: If True, enable verbose debug output.
    """
    _apply_verbose(verbose)
    from rhiza_tools.commands.rollback import RollbackOptions

    options = RollbackOptions(
        tag=tag,
        revert_bump=revert_bump,
        dry_run=dry_run,
        non_interactive=non_interactive,
    )
    rollback_command(options)


@app.command(name="update-readme")
def update_readme(
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
    verbose: bool = VERBOSE_OPTION,
) -> None:
    """Update README.md with the current output from `make help`.

    This command runs `make help` and updates the README.md file with the current
    help output, keeping the documentation in sync with available Make targets.

    Args:
        dry_run: If True, show the help output that would be inserted without
            actually modifying README.md.
        verbose: If True, enable verbose debug output.
    """
    _apply_verbose(verbose)
    update_readme_command(dry_run)


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
    used in GitHub Actions to compute the test matrix.

    Args:
        pyproject: Path to the pyproject.toml file.
        candidates: Comma-separated list of candidate Python versions to evaluate.
            Defaults to "3.11,3.12,3.13,3.14".
        verbose: If True, enable verbose debug output.
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

    Args:
        benchmarks_json: Path to the benchmarks.json file.
        output_html: Path where the HTML visualization should be saved.
        show: If True, open the interactive chart in a browser after saving.
        verbose: If True, enable verbose debug output.
    """
    _apply_verbose(verbose)
    analyze_benchmarks_command(benchmarks_json=benchmarks_json, output_html=output_html, show=show)
