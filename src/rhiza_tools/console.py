"""Console output utilities for rhiza-tools CLI.

Provides clean, user-facing output functions using typer.echo/secho,
which is the standard approach for Click/Typer-based CLIs. Loguru is
reserved for debug/diagnostic output and is only enabled when the user
passes --verbose.

Usage in commands::

    from rhiza_tools.console import console

    console.info("Current version: 1.0.0")
    console.success("Version bumped successfully!")
    console.warning("Branch is ahead of remote")
    console.error("pyproject.toml not found")
"""

import sys

import typer
from loguru import logger

_verbose: bool = False


def configure(*, verbose: bool = False) -> None:
    """Configure console output and logging verbosity.

    Removes loguru's default stderr handler so that loguru output is
    suppressed by default. When *verbose* is ``True``, a handler is
    re-added at DEBUG level.

    This should be called once from the CLI callback before any command
    runs.

    Args:
        verbose: If True, enable loguru debug output on stderr.
    """
    global _verbose
    _verbose = verbose

    # Remove all default loguru handlers (the default one logs to stderr at DEBUG)
    logger.remove()

    if verbose:
        logger.add(sys.stderr, level="DEBUG")


def is_verbose() -> bool:
    """Return whether verbose mode is currently enabled."""
    return _verbose


def info(message: str) -> None:
    """Print an informational message to stdout.

    Args:
        message: The message to display.
    """
    typer.echo(message)


def success(message: str) -> None:
    """Print a success message to stdout.

    Args:
        message: The message to display.
    """
    typer.echo(message)


def warning(message: str) -> None:
    """Print a warning message to stderr.

    Args:
        message: The message to display.
    """
    typer.secho(message, fg=typer.colors.YELLOW, err=True)


def error(message: str) -> None:
    """Print an error message to stderr.

    Args:
        message: The message to display.
    """
    typer.secho(message, fg=typer.colors.RED, err=True)
