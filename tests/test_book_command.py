"""Tests for the book command in rhiza_tools.commands.book.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from rhiza_tools.cli import app

runner = CliRunner()


def test_book_command_dry_run(capsys):
    """Test the book command with dry-run option."""
    result = runner.invoke(app, ["book", "--dry-run"])
    assert result.exit_code == 0
    # Just verify command runs without error in dry-run mode


def test_book_command_creates_directory_structure(tmp_path, monkeypatch):
    """Test that the book command creates the expected directory structure."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create mock source directories with content
    pdoc_dir = tmp_path / "_pdoc"
    pdoc_dir.mkdir()
    (pdoc_dir / "index.html").write_text("<html>API Docs</html>")

    coverage_dir = tmp_path / "_tests" / "html-coverage"
    coverage_dir.mkdir(parents=True)
    (coverage_dir / "index.html").write_text("<html>Coverage</html>")

    test_report_dir = tmp_path / "_tests" / "html-report"
    test_report_dir.mkdir(parents=True)
    (test_report_dir / "report.html").write_text("<html>Test Report</html>")

    marimushka_dir = tmp_path / "_marimushka"
    marimushka_dir.mkdir()
    (marimushka_dir / "index.html").write_text("<html>Notebooks</html>")

    # Run the command
    result = runner.invoke(app, ["book"])
    assert result.exit_code == 0

    # Verify _book directory was created
    book_dir = tmp_path / "_book"
    assert book_dir.exists()

    # Verify subdirectories and files were copied
    assert (book_dir / "pdoc" / "index.html").exists()
    assert (book_dir / "tests" / "html-coverage" / "index.html").exists()
    assert (book_dir / "tests" / "html-report" / "report.html").exists()
    assert (book_dir / "marimushka" / "index.html").exists()

    # Verify links.json was created with correct content
    links_json = book_dir / "links.json"
    assert links_json.exists()

    links = json.loads(links_json.read_text())
    assert "API" in links
    assert "Coverage" in links
    assert "Test Report" in links
    assert "Notebooks" in links


def test_book_command_handles_missing_directories(tmp_path, monkeypatch):
    """Test that the book command handles missing source directories gracefully."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create only pdoc directory (others missing)
    pdoc_dir = tmp_path / "_pdoc"
    pdoc_dir.mkdir()
    (pdoc_dir / "index.html").write_text("<html>API Docs</html>")

    # Run the command
    result = runner.invoke(app, ["book"])
    assert result.exit_code == 0

    # Verify _book directory was created
    book_dir = tmp_path / "_book"
    assert book_dir.exists()

    # Verify only pdoc was copied
    assert (book_dir / "pdoc" / "index.html").exists()
    assert not (book_dir / "tests" / "html-coverage").exists()
    assert not (book_dir / "tests" / "html-report").exists()
    assert not (book_dir / "marimushka").exists()

    # Verify links.json contains only API
    links_json = book_dir / "links.json"
    assert links_json.exists()

    links = json.loads(links_json.read_text())
    assert "API" in links
    assert "Coverage" not in links
    assert "Test Report" not in links
    assert "Notebooks" not in links


def test_book_command_generates_coverage_badge(tmp_path, monkeypatch):
    """Test that the book command generates coverage badge when coverage.json exists."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create coverage directory with coverage.json
    tests_dir = tmp_path / "_tests"
    coverage_dir = tests_dir / "html-coverage"
    coverage_dir.mkdir(parents=True)
    (coverage_dir / "index.html").write_text("<html>Coverage</html>")

    coverage_json = tests_dir / "coverage.json"
    coverage_data = {"totals": {"percent_covered": 85.5}}
    coverage_json.write_text(json.dumps(coverage_data))

    # Create a mock script directory
    scripts_dir = tmp_path / ".rhiza" / "scripts"
    scripts_dir.mkdir(parents=True)

    # Create a simple mock script that creates the badge file
    mock_script = scripts_dir / "generate-coverage-badge.sh"
    mock_script.write_text(
        """#!/bin/sh
set -e
mkdir -p _book/tests
echo '{"schemaVersion":1,"label":"coverage","message":"86%","color":"green"}' > _book/tests/coverage-badge.json
"""
    )
    mock_script.chmod(0o755)

    # Run the command
    result = runner.invoke(app, ["book"])
    assert result.exit_code == 0

    # Verify coverage badge was generated
    badge_json = tmp_path / "_book" / "tests" / "coverage-badge.json"
    assert badge_json.exists()


def test_book_command_cleans_existing_book_directory(tmp_path, monkeypatch):
    """Test that the book command cleans existing _book directory."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create existing _book directory with old content
    book_dir = tmp_path / "_book"
    book_dir.mkdir()
    old_file = book_dir / "old_file.txt"
    old_file.write_text("old content")

    # Create new content
    pdoc_dir = tmp_path / "_pdoc"
    pdoc_dir.mkdir()
    (pdoc_dir / "index.html").write_text("<html>API Docs</html>")

    # Run the command
    result = runner.invoke(app, ["book"])
    assert result.exit_code == 0

    # Verify old content was removed
    assert not old_file.exists()

    # Verify new content exists
    assert (book_dir / "pdoc" / "index.html").exists()


def test_book_command_cli_integration():
    """Test the book command is properly integrated in CLI."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "book" in result.stdout
