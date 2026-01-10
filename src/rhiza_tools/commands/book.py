"""Command to build the documentation book."""

import json
import shutil
import subprocess
from pathlib import Path

from loguru import logger


def _run_generate_coverage_badge() -> bool:
    """Run the generate-coverage-badge.sh script.

    Returns:
        True if successful, False otherwise.
    """
    scripts_folder = Path(".rhiza") / "scripts"
    script_path = scripts_folder / "generate-coverage-badge.sh"

    if not script_path.exists():
        logger.warning(f"Coverage badge script not found at {script_path}")
        return False

    try:
        subprocess.run(
            ["/bin/sh", str(script_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Coverage badge generated successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate coverage badge: {e.stderr}")
        return False


def book_command(dry_run: bool = False):
    """Build the combined documentation book.

    Assembles the combined documentation site into _book by:
    - Copying API docs (pdoc), coverage, test report, and marimo exports
    - Generating a links.json consumed by minibook
    """
    logger.info("Building combined documentation...")
    logger.info("Assembling book...")

    if dry_run:
        logger.info("[DRY RUN] Would delete the _book folder")
        logger.info("[DRY RUN] Would create empty _book folder")
        logger.info("[DRY RUN] Would copy documentation artifacts")
        return

    # Delete and recreate _book folder
    logger.info("Delete the _book folder...")
    book_dir = Path("_book")
    if book_dir.exists():
        shutil.rmtree(book_dir)

    logger.info("Create empty _book folder...")
    book_dir.mkdir(parents=True, exist_ok=True)

    # Start building links.json content
    links = {}

    # Copy API docs
    logger.info("Copy API docs...")
    pdoc_dir = Path("_pdoc")
    if (pdoc_dir / "index.html").exists():
        book_pdoc_dir = book_dir / "pdoc"
        book_pdoc_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(pdoc_dir, book_pdoc_dir, dirs_exist_ok=True)
        links["API"] = "./pdoc/index.html"
        logger.info("Copied API docs into _book/pdoc")
    else:
        logger.warning("No API docs found or directory is empty")

    # Copy coverage report
    logger.info("Copy coverage report...")
    coverage_dir = Path("_tests") / "html-coverage"
    if (coverage_dir / "index.html").exists():
        book_coverage_dir = book_dir / "tests" / "html-coverage"
        book_coverage_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(coverage_dir, book_coverage_dir, dirs_exist_ok=True)
        links["Coverage"] = "./tests/html-coverage/index.html"
        logger.info("Copied coverage report into _book/tests/html-coverage")

        # Generate coverage badge JSON if coverage.json exists
        coverage_json = Path("_tests") / "coverage.json"
        if coverage_json.exists():
            logger.info("Generating coverage badge...")
            _run_generate_coverage_badge()
    else:
        logger.warning("No coverage report found or directory is empty")

    # Copy test report
    logger.info("Copy test report...")
    test_report_dir = Path("_tests") / "html-report"
    if (test_report_dir / "report.html").exists():
        book_test_dir = book_dir / "tests" / "html-report"
        book_test_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(test_report_dir, book_test_dir, dirs_exist_ok=True)
        links["Test Report"] = "./tests/html-report/report.html"
        logger.info("Copied test report into _book/tests/html-report")
    else:
        logger.warning("No test report found or directory is empty")

    # Copy notebooks
    logger.info("Copy notebooks...")
    marimushka_dir = Path("_marimushka")
    if (marimushka_dir / "index.html").exists():
        book_notebooks_dir = book_dir / "marimushka"
        book_notebooks_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(marimushka_dir, book_notebooks_dir, dirs_exist_ok=True)
        links["Notebooks"] = "./marimushka/index.html"
        logger.info("Copied notebooks into _book/marimushka")
    else:
        logger.warning("No notebooks found or directory is empty")

    # Write final links.json
    links_json_path = book_dir / "links.json"
    with open(links_json_path, "w") as f:
        json.dump(links, f, indent=2)

    logger.info("Generated links.json:")
    logger.info(json.dumps(links, indent=2))
    logger.success("Book assembly completed successfully")
