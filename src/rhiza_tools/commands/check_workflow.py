"""Command to check GitHub Actions workflow files for the (RHIZA) prefix.

This module provides functionality to validate that workflow files have the
correct naming prefix and optionally update them if they don't.

Example:
    Check a workflow file::

        from rhiza_tools.commands.check_workflow import check_workflow_command
        check_workflow_command(["workflow.yml"])

    Check multiple workflow files::

        check_workflow_command([".github/workflows/ci.yml", ".github/workflows/test.yml"])
"""

from pathlib import Path

import typer
import yaml
from loguru import logger


def check_file(filepath: str) -> bool:
    """Check if the workflow file has the correct name prefix and update if needed.

    Args:
        filepath: Path to the workflow file.

    Returns:
        bool: True if file is correct, False if it was updated or has errors.
    """
    with open(filepath) as f:
        try:
            content = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            logger.error(f"Error parsing YAML {filepath}: {exc}")
            return False

    if not isinstance(content, dict):
        # Empty file or not a dict
        return True

    name = content.get("name")
    if not name:
        logger.error(f"Error: {filepath} missing 'name' field.")
        return False

    if not name.startswith("(RHIZA) "):
        logger.info(f"Updating {filepath}: name '{name}' -> '(RHIZA) {name}'")

        # Read file lines to perform replacement while preserving comments
        with open(filepath) as f_read:
            lines = f_read.readlines()

        with open(filepath, "w") as f_write:
            replaced = False
            for line in lines:
                # Replace only the top-level name field (assumes it starts at beginning of line)
                if not replaced and line.startswith("name:"):
                    # Check if this line corresponds to the extracted name.
                    # Simple check: does it contain reasonable parts of the name?
                    # Or just blinding replace top-level name:
                    # We'll use quotes to be safe
                    f_write.write(f'name: "(RHIZA) {name}"\n')
                    replaced = True
                else:
                    f_write.write(line)

        return False  # Fail so pre-commit knows files were modified

    return True


def check_workflow_command(files: list[str]) -> None:
    """Check GitHub Actions workflow files for correct naming prefix.

    This command validates that workflow files have the "(RHIZA) " prefix in
    their name field. If a workflow file doesn't have the correct prefix, it
    will be automatically updated.

    Args:
        files: List of workflow file paths to check.

    Raises:
        typer.Exit: If any files were updated or had errors (exit code 1).

    Example:
        Check workflow files::

            check_workflow_command([".github/workflows/ci.yml"])

        Check multiple files::

            check_workflow_command([
                ".github/workflows/ci.yml",
                ".github/workflows/test.yml"
            ])
    """
    if not files:
        logger.error("No workflow files specified")
        raise typer.Exit(code=1)

    failed = False
    for file in files:
        file_path = Path(file)
        if not file_path.exists():
            logger.error(f"File not found: {file}")
            failed = True
            continue

        if not check_file(file):
            failed = True

    if failed:
        logger.info("Some workflow files were updated or had errors")
        raise typer.Exit(code=1)
    else:
        logger.success("All workflow files have correct naming prefix")
