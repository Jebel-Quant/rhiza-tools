"""CLI commands for Rhiza Tools."""

from pathlib import Path

import typer

from .commands.bump import bump_command
from .commands.generate_badges import generate_badges_command

app = typer.Typer(help="Rhiza Tools - Extra utilities for Rhiza.")


@app.command()
def bump(
    version: str | None = typer.Argument(None, help="The version to bump to (e.g., 1.0.1, major, minor, patch, etc)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
    commit: bool = typer.Option(False, "--commit", help="Commit the changes to git."),
    allow_dirty: bool = typer.Option(
        False, "--allow-dirty", help="Allow bumping even if the working directory is dirty."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output from bump-my-version."),
):
    """Bump the version of the project."""
    bump_command(version, dry_run, commit, allow_dirty, verbose)


@app.command()
def release(
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
):
    """Create a git tag and push to remote to trigger the release workflow."""
    if dry_run:
        typer.echo("Would create and push release tag")
    else:
        typer.echo("Creating and pushing release tag")
        # TODO: Implement actual release logic here (port from release.sh)


@app.command(name="update-readme-help")
def update_readme_help(
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
):
    """Update README.md with the current output from `make help`."""
    if dry_run:
        typer.echo("Would update README.md with make help output")
    else:
        typer.echo("Updating README.md with make help output")
        # TODO: Implement actual update-readme-help logic here (port from update-readme-help.sh)


@app.command(name="generate-badges")
def generate_badges(
    badges: list[str] | None = typer.Option(
        None,
        "--badges",
        "-b",
        help="Comma-separated list of badges to generate (e.g., 'coverage,license,pypi-version'). "
        "If not specified, reads from .rhiza/.cfg.toml or generates only synced-with-rhiza.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Path to output directory. Defaults to config or _book/badges.",
    ),
    all_badges: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Generate all available badges.",
    ),
    update_readme: bool = typer.Option(
        False,
        "--update-readme",
        "-u",
        help="Add or update badge markdown in README.md.",
    ),
    readme_path: Path | None = typer.Option(
        None,
        "--readme",
        help="Path to README.md file. Defaults to README.md in current directory.",
    ),
    badge_url_base: str | None = typer.Option(
        None,
        "--badge-url-base",
        help="Base URL for hosted badges (e.g., https://org.github.io/repo/badges).",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
):
    """Generate badge endpoint JSON files for your project.

    Creates JSON files compatible with shields.io's endpoint badge feature.
    These can be hosted (e.g., on GitHub Pages) and referenced in your README.

    Badge names: synced-with-rhiza, coverage, pypi-version, license,
    python-versions, downloads, codefactor

    Examples:
        # Generate specific badges
        rhiza-tools generate-badges --badges coverage,license,pypi-version

        # Generate all badges and update README
        rhiza-tools generate-badges --all --update-readme

    Configuration in .rhiza/.cfg.toml:

        [tool.generate-badges]
        output_dir = "_book/badges"
        badges = ["synced-with-rhiza", "coverage", "license"]
    """
    generate_badges_command(
        output_dir=output_dir,
        badges=badges,
        all_badges=all_badges,
        update_readme=update_readme,
        readme_path=readme_path,
        badge_url_base=badge_url_base,
        dry_run=dry_run,
    )
