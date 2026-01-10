"""Command to export Marimo notebooks to HTML using marimushka."""

import os
import subprocess
from pathlib import Path

import typer
from loguru import logger


def marimushka_command(
    marimo_folder: str = "book/marimo",
    output: str = "_marimushka",
    uv_bin: str | None = None,
    uvx_bin: str | None = None,
):
    """Export Marimo notebooks to HTML.

    Args:
        marimo_folder: Path to folder containing Marimo notebooks
        output: Output directory for HTML files
        uv_bin: Path to uv binary (defaults to ./bin/uv or uv in PATH)
        uvx_bin: Path to uvx binary (defaults to ./bin/uvx or uvx in PATH)
    """
    # Resolve binaries
    if uvx_bin is None:
        uvx_bin = os.environ.get("UVX_BIN", "./bin/uvx")
    if uv_bin is None:
        uv_bin = os.environ.get("UV_BIN", "./bin/uv")

    logger.info(f"Exporting notebooks from {marimo_folder}...")

    marimo_path = Path(marimo_folder)
    output_path = Path(output)

    # Check if marimo folder exists
    if not marimo_path.exists():
        logger.warning(f"Directory '{marimo_folder}' does not exist. Skipping marimushka.")
        return

    # Ensure output directory exists
    output_path.mkdir(parents=True, exist_ok=True)

    # Find Python files in marimo folder
    py_files = list(marimo_path.glob("*.py"))

    if not py_files:
        logger.warning(f"No Python files found in '{marimo_folder}'.")
        # Create a minimal index.html indicating no notebooks
        index_html = output_path / "index.html"
        index_html.write_text(
            "<html><head><title>Marimo Notebooks</title></head>"
            "<body><h1>Marimo Notebooks</h1><p>No notebooks found.</p></body></html>"
        )
        return

    # Resolve paths to absolute
    current_dir = Path.cwd()
    output_abs = (current_dir / output_path).resolve()

    # Resolve uvx_bin to absolute path if it's a relative path
    uvx_path = Path(uvx_bin)
    if not uvx_path.is_absolute() and "/" in uvx_bin:
        uvx_path = (current_dir / uvx_path).resolve()
        uvx_bin = str(uvx_path)

    # Resolve uv_bin to absolute path
    uv_path = Path(uv_bin)
    if not uv_path.is_absolute() and "/" in uv_bin:
        uv_path = (current_dir / uv_path).resolve()
        uv_bin = str(uv_path)

    # Derive UV_INSTALL_DIR from UV_BIN
    uv_install_dir = Path(uv_bin).parent

    # Change to notebook directory
    original_dir = Path.cwd()
    os.chdir(marimo_path)

    try:
        # Run marimushka export
        cmd = [
            str(uvx_bin),
            "marimushka>=0.1.9",
            "export",
            "--notebooks",
            ".",
            "--output",
            str(output_abs),
            "--bin-path",
            str(uv_install_dir),
        ]

        logger.debug(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            logger.error(f"marimushka export failed: {result.stderr}")
            raise typer.Exit(code=1)

        # Create .nojekyll file for GitHub Pages
        nojekyll = output_abs / ".nojekyll"
        nojekyll.touch()

        logger.success(f"Notebooks exported successfully to {output}")

    finally:
        # Change back to original directory
        os.chdir(original_dir)
