"""Command to update README.md with the current output from `make help`.

This module provides functionality to automatically synchronize the README.md
file with the current Makefile help output, keeping documentation up to date.

Example:
    Update README with make help::

        from rhiza_tools.commands.update_readme import update_readme_command
        update_readme_command()

    Preview changes with dry run::

        update_readme_command(dry_run=True)
"""

import re
import subprocess  # nosec B404
from pathlib import Path

import typer
from loguru import logger


def _get_make_help_output() -> str:
    """Generate the help output from Makefile.

    Runs `make help` and returns the output with ANSI codes stripped and
    make directory messages filtered out.

    Returns:
        The help output as a clean string without ANSI codes or directory messages.

    Raises:
        typer.Exit: If make command is not found or execution fails.

    Example:
        >>> help_output = _get_make_help_output()  # doctest: +SKIP
        >>> print(help_output)  # doctest: +SKIP
        install                Install dependencies using uv
        test                   Run tests with pytest
        ...
    """
    try:
        # Run make help and capture output
        result = subprocess.run(  # nosec B603 B607
            ["make", "help"],
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit
        )

        # Get stdout and filter it
        output = result.stdout

        # Strip ANSI color codes (escape sequences)
        # Pattern matches: ESC [ <numbers/semicolons> m
        output = re.sub(r"\x1b\[[0-9;]*m", "", output)

        # Filter out make's directory change messages
        lines = output.split("\n")
        filtered_lines = []
        for line in lines:
            # Skip lines starting with "make[" or containing directory messages
            if line.startswith("make[") or "Entering directory" in line or "Leaving directory" in line:
                continue
            filtered_lines.append(line)

        return "\n".join(filtered_lines)

    except FileNotFoundError:
        logger.error("make command not found")
        raise typer.Exit(code=1) from None
    except Exception as e:
        logger.error(f"Failed to run 'make help': {e}")
        raise typer.Exit(code=1) from None


def _read_readme_content(readme_path: Path) -> str:
    """Read content from README file.

    Args:
        readme_path: Path to the README.md file.

    Returns:
        The content of the README file.

    Raises:
        typer.Exit: If README cannot be read.
    """
    try:
        return readme_path.read_text()
    except FileNotFoundError:
        logger.error(f"README file not found: {readme_path}")
        raise typer.Exit(code=1) from None
    except Exception as e:
        logger.error(f"Failed to read README: {e}")
        raise typer.Exit(code=1) from None


def _write_readme_content(readme_path: Path, content: str) -> None:
    """Write content to README file.

    Args:
        readme_path: Path to the README.md file.
        content: The content to write.

    Raises:
        typer.Exit: If README cannot be written.
    """
    try:
        readme_path.write_text(content)
    except Exception as e:
        logger.error(f"Failed to write README: {e}")
        raise typer.Exit(code=1) from None


def _replace_code_block_content(lines: list[str], start_idx: int, help_output: str) -> tuple[list[str], int]:
    """Replace content within a code block after the marker.

    Args:
        lines: List of lines from the README.
        start_idx: Index where the code block should start.
        help_output: The new content to insert.

    Returns:
        Tuple of (new lines to add, next index to process).
        Returns empty list and same index if code fence not found.
    """
    new_lines = []
    i = start_idx

    # Skip empty line if present
    if i < len(lines) and lines[i].strip() == "":
        new_lines.append(lines[i])
        i += 1

    # Check for opening code fence
    if i >= len(lines) or lines[i].strip() != "```makefile":
        return [], start_idx

    new_lines.append(lines[i])
    i += 1

    # Add the new help output
    new_lines.append(help_output)

    # Skip old content until we find the closing fence
    while i < len(lines) and lines[i].strip() != "```":
        i += 1

    # Add the closing fence if found
    if i < len(lines):
        new_lines.append(lines[i])
        i += 1

    return new_lines, i


def _update_readme_with_help(readme_path: Path, help_output: str) -> bool:
    """Update README.md with new help output.

    Searches for the marker line and updates the code block that follows it
    with the new help output.

    Args:
        readme_path: Path to the README.md file.
        help_output: The help output to insert.

    Returns:
        True if the README was updated, False if the marker was not found.

    Raises:
        typer.Exit: If README cannot be read or written.

    Example:
        >>> from pathlib import Path
        >>> updated = _update_readme_with_help(  # doctest: +SKIP
        ...     Path("README.md"),
        ...     "install    Install dependencies"
        ... )
        >>> print(updated)  # doctest: +SKIP
        True
    """
    content = _read_readme_content(readme_path)
    marker = "Run `make help` to see all available targets:"

    if marker not in content:
        logger.info("No help section marker found in README.md - skipping update")
        return False

    lines = content.split("\n")
    new_lines = []
    i = 0
    pattern_found = False

    while i < len(lines):
        line = lines[i]

        if line.strip() == marker:
            new_lines.append(line)
            i += 1

            block_lines, new_idx = _replace_code_block_content(lines, i, help_output)
            if block_lines:
                new_lines.extend(block_lines)
                i = new_idx
                pattern_found = True
            else:
                logger.warning("Help section marker found but no code fence follows - skipping update")
        else:
            new_lines.append(line)
            i += 1

    if not pattern_found:
        logger.info("Help section not properly formatted in README.md - skipping update")
        return False

    _write_readme_content(readme_path, "\n".join(new_lines))
    return True


def update_readme_command(dry_run: bool = False):
    """Update README.md with the current output from `make help`.

    This command synchronizes the README.md file with the current Makefile help
    output by finding the marker line and updating the code block that follows.

    Args:
        dry_run: If True, only show what would be done without making changes.

    Raises:
        typer.Exit: If README.md is not found or cannot be accessed.

    Example:
        Update README::

            update_readme_command()

        Preview changes::

            update_readme_command(dry_run=True)
    """
    readme_path = Path("README.md")

    if not readme_path.exists():
        logger.error("README.md not found in current directory")
        raise typer.Exit(code=1)

    # Get the help output
    logger.info("Generating help output from Makefile...")
    help_output = _get_make_help_output()

    if dry_run:
        logger.info("DRY RUN: Would update README.md with the following content:")
        logger.info("-" * 50)
        logger.info(help_output)
        logger.info("-" * 50)
        return

    # Update the README
    logger.info("Updating README.md...")
    updated = _update_readme_with_help(readme_path, help_output)

    if updated:
        logger.success("README.md updated with current 'make help' output")
    else:
        logger.info("README.md was not modified (no marker found)")
