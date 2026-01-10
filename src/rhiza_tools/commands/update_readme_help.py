"""Command to update README.md with the current output from `make help`."""

import re
import subprocess
from pathlib import Path

import typer
from loguru import logger


def _get_make_help_output() -> str:
    """Generate the help output from Makefile.

    Returns:
        The help output with ANSI codes stripped and make directory messages filtered out.
    """
    try:
        # Run make help and capture output
        result = subprocess.run(
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
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Failed to run 'make help': {e}")
        raise typer.Exit(code=1)


def _update_readme_with_help(readme_path: Path, help_output: str) -> bool:
    """Update README.md with new help output.

    Args:
        readme_path: Path to the README.md file.
        help_output: The help output to insert.

    Returns:
        True if the README was updated, False if the marker was not found.
    """
    try:
        content = readme_path.read_text()
    except FileNotFoundError:
        logger.error(f"README file not found: {readme_path}")
        raise typer.Exit(code=1)
    except Exception as e:
        logger.error(f"Failed to read README: {e}")
        raise typer.Exit(code=1)

    # Look for the marker pattern
    marker = "Run `make help` to see all available targets:"

    if marker not in content:
        logger.info("No help section marker found in README.md - skipping update")
        return False

    # Split content into lines for processing
    lines = content.split("\n")
    new_lines = []
    i = 0
    pattern_found = False

    while i < len(lines):
        line = lines[i]

        # Check if this is the marker line
        if line.strip() == marker:
            # Add the marker line
            new_lines.append(line)
            pattern_found = True
            i += 1

            # Skip empty line if present
            if i < len(lines) and lines[i].strip() == "":
                new_lines.append(lines[i])
                i += 1

            # Check for opening code fence
            if i < len(lines) and lines[i].strip() == "```makefile":
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
            else:
                # If no code fence found, just continue
                continue
        else:
            new_lines.append(line)
            i += 1

    if not pattern_found:
        logger.info("No help section marker found in README.md - skipping update")
        return False

    # Write the updated content
    try:
        readme_path.write_text("\n".join(new_lines))
        return True
    except Exception as e:
        logger.error(f"Failed to write README: {e}")
        raise typer.Exit(code=1)


def update_readme_help_command(dry_run: bool = False):
    """Update README.md with the current output from `make help`.

    Args:
        dry_run: If True, only show what would be done without making changes.
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
