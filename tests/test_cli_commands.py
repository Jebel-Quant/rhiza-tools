"""Tests for CLI commands in rhiza_tools.cli.py."""

from unittest.mock import MagicMock

from typer.testing import CliRunner

from rhiza_tools import __version__
from rhiza_tools.cli import app

runner = CliRunner()


def test_version_flag():
    """Test the --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "rhiza-tools version" in result.stdout
    # Check that it displays the actual version from the package
    assert __version__ in result.stdout


def test_version_matrix_command(monkeypatch, tmp_path):
    """The version-matrix command forwards the pyproject path to the command function."""
    # Create a temporary pyproject.toml
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-project"
classifiers = ["Programming Language :: Python :: 3.11"]
""")

    # Mock the command function
    mock_version_matrix = MagicMock()
    monkeypatch.setattr("rhiza_tools.cli.version_matrix_command", mock_version_matrix)

    result = runner.invoke(app, ["version-matrix", "--pyproject", str(pyproject)])
    assert result.exit_code == 0
    mock_version_matrix.assert_called_once_with(pyproject_path=pyproject)
