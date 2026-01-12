"""CLI commands for Rhiza Tools."""

import typer

from .commands.bump import bump_command
from .commands.update_readme import update_readme_command

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


@app.command(name="update-readme")
def update_readme(
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
):
    """Update README.md with the current output from `make help`."""
    update_readme_command(dry_run)
