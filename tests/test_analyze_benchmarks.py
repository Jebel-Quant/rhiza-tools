"""Tests for analyze_benchmarks command."""

import json
from unittest.mock import patch

import pytest

from rhiza_tools.commands.analyze_benchmarks import analyze_benchmarks_command


@pytest.fixture
def valid_benchmark_data():
    """Create valid benchmark data for testing."""
    return {
        "benchmarks": [
            {
                "name": "test_string_concatenation",
                "stats": {"mean": 0.000005},
            },
            {
                "name": "test_dictionary_operations",
                "stats": {"mean": 0.00001},
            },
            {
                "name": "test_list_comprehension",
                "stats": {"mean": 0.000025},
            },
        ]
    }


@pytest.fixture
def benchmark_json_file(tmp_path, valid_benchmark_data):
    """Create a temporary benchmark JSON file."""
    json_file = tmp_path / "benchmarks.json"
    json_file.write_text(json.dumps(valid_benchmark_data))
    return json_file


def test_analyze_benchmarks_missing_dependencies(tmp_path):
    """Test analyze_benchmarks with missing dependencies."""
    json_file = tmp_path / "benchmarks.json"
    json_file.write_text(json.dumps({"benchmarks": []}))

    # Mock the import to raise ImportError
    with patch("builtins.__import__", side_effect=ImportError("No module named 'pandas'")):
        with pytest.raises(SystemExit) as exc_info:
            analyze_benchmarks_command(benchmarks_json=json_file)
        assert exc_info.value.code == 1


def test_analyze_benchmarks_file_not_found(tmp_path):
    """Test analyze_benchmarks when JSON file doesn't exist."""
    non_existent = tmp_path / "nonexistent.json"

    with pytest.raises(SystemExit) as exc_info:
        analyze_benchmarks_command(benchmarks_json=non_existent)

    assert exc_info.value.code == 0


def test_analyze_benchmarks_invalid_json(tmp_path):
    """Test analyze_benchmarks with invalid JSON."""
    json_file = tmp_path / "invalid.json"
    json_file.write_text("{ invalid json }")

    with pytest.raises(SystemExit) as exc_info:
        analyze_benchmarks_command(benchmarks_json=json_file)

    assert exc_info.value.code == 0


def test_analyze_benchmarks_missing_benchmarks_key(tmp_path):
    """Test analyze_benchmarks with missing 'benchmarks' key."""
    json_file = tmp_path / "no_benchmarks.json"
    json_file.write_text(json.dumps({"results": []}))

    with pytest.raises(SystemExit) as exc_info:
        analyze_benchmarks_command(benchmarks_json=json_file)

    assert exc_info.value.code == 0


def test_analyze_benchmarks_empty_benchmarks(tmp_path):
    """Test analyze_benchmarks with empty benchmarks list."""
    json_file = tmp_path / "empty_benchmarks.json"
    json_file.write_text(json.dumps({"benchmarks": []}))

    with pytest.raises(SystemExit) as exc_info:
        analyze_benchmarks_command(benchmarks_json=json_file)

    assert exc_info.value.code == 0


def test_analyze_benchmarks_success(benchmark_json_file, tmp_path):
    """Test successful analyze_benchmarks execution."""
    output_html = tmp_path / "output.html"

    # Run command (show=False by default, so fig.show() must not be called)
    analyze_benchmarks_command(benchmarks_json=benchmark_json_file, output_html=output_html)

    # Verify output file was created
    assert output_html.exists()
    assert output_html.stat().st_size > 0


def test_analyze_benchmarks_show_false_does_not_open_browser(benchmark_json_file, tmp_path):
    """Test that fig.show() is not called when show=False (the default)."""
    output_html = tmp_path / "output.html"

    with patch("plotly.graph_objs._figure.Figure.show") as mock_show:
        analyze_benchmarks_command(benchmarks_json=benchmark_json_file, output_html=output_html, show=False)

    mock_show.assert_not_called()


def test_analyze_benchmarks_show_true_opens_browser(benchmark_json_file, tmp_path):
    """Test that fig.show() is called when show=True."""
    output_html = tmp_path / "output.html"

    with patch("plotly.graph_objs._figure.Figure.show") as mock_show:
        analyze_benchmarks_command(benchmarks_json=benchmark_json_file, output_html=output_html, show=True)

    mock_show.assert_called_once()


def test_analyze_benchmarks_default_paths(valid_benchmark_data, tmp_path, monkeypatch):
    """Test analyze_benchmarks with default paths."""
    # Create default path structure
    benchmarks_dir = tmp_path / "_benchmarks"
    benchmarks_dir.mkdir()
    default_json = benchmarks_dir / "benchmarks.json"
    default_json.write_text(json.dumps(valid_benchmark_data))

    # Change to tmp directory and run with default paths (show=False by default)
    monkeypatch.chdir(tmp_path)
    analyze_benchmarks_command()

    # Verify output file was created at default location
    output_html = tmp_path / "_benchmarks" / "benchmarks.html"
    assert output_html.exists()
    assert output_html.stat().st_size > 0
