"""CLI commands for Rhiza Tools."""

import typer

from .commands.bump import bump_command

app = typer.Typer(help="Rhiza Tools - Extra utilities for Rhiza.")


@app.command()
def bump(
    version: str | None = typer.Argument(None, help="The version to bump to (e.g., 1.0.1, major, minor, patch)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print what would happen without doing it."),
):
    """Bump the version of the project."""
    bump_command(version, dry_run)


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


if __name__ == "__main__":
    app()
