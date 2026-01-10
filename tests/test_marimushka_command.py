"""Tests for the marimushka command."""

from unittest.mock import MagicMock, patch

import pytest
from click.exceptions import Exit

from rhiza_tools.commands.marimushka import marimushka_command


def test_marimushka_command_missing_folder(tmp_path, monkeypatch):
    """Test marimushka command when marimo folder is missing."""
    monkeypatch.chdir(tmp_path)

    # Should not raise an exception, just return early
    marimushka_command(marimo_folder="missing", output="_marimushka")

    # Output folder should not be created when input doesn't exist
    assert not (tmp_path / "_marimushka").exists()


def test_marimushka_command_no_python_files(tmp_path, monkeypatch):
    """Test marimushka command when marimo folder has no Python files."""
    monkeypatch.chdir(tmp_path)

    # Create marimo folder without Python files
    marimo_folder = tmp_path / "book" / "marimo"
    marimo_folder.mkdir(parents=True)

    output_folder = tmp_path / "_marimushka"

    marimushka_command(marimo_folder="book/marimo", output="_marimushka")

    # Should create minimal index.html
    assert output_folder.exists()
    assert (output_folder / "index.html").exists()
    assert "No notebooks found" in (output_folder / "index.html").read_text()


@patch("subprocess.run")
def test_marimushka_command_success(mock_run, tmp_path, monkeypatch):
    """Test successful execution of marimushka command."""
    monkeypatch.chdir(tmp_path)

    # Create marimo folder with a Python file
    marimo_folder = tmp_path / "book" / "marimo"
    marimo_folder.mkdir(parents=True)
    (marimo_folder / "notebook.py").write_text("# test notebook")

    output_folder = tmp_path / "_marimushka"

    # Mock subprocess.run to simulate successful execution
    mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

    # Create bin directory for uv/uvx
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "uv").touch()
    (bin_dir / "uvx").touch()

    marimushka_command(
        marimo_folder="book/marimo",
        output="_marimushka",
        uv_bin=str(bin_dir / "uv"),
        uvx_bin=str(bin_dir / "uvx"),
    )

    # Verify subprocess was called
    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert "marimushka>=0.1.9" in call_args
    assert "export" in call_args
    assert "--notebooks" in call_args
    assert "--output" in call_args
    assert "--bin-path" in call_args

    # Verify .nojekyll was created
    assert (output_folder / ".nojekyll").exists()


@patch("subprocess.run")
def test_marimushka_command_with_env_vars(mock_run, tmp_path, monkeypatch):
    """Test marimushka command using environment variables."""
    monkeypatch.chdir(tmp_path)

    # Create marimo folder with a Python file
    marimo_folder = tmp_path / "book" / "marimo"
    marimo_folder.mkdir(parents=True)
    (marimo_folder / "notebook.py").write_text("# test notebook")

    # Create bin directory
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "uv").touch()
    (bin_dir / "uvx").touch()

    # Set environment variables
    monkeypatch.setenv("UV_BIN", str(bin_dir / "uv"))
    monkeypatch.setenv("UVX_BIN", str(bin_dir / "uvx"))

    # Mock subprocess.run
    mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

    marimushka_command(marimo_folder="book/marimo", output="_marimushka")

    # Verify subprocess was called
    assert mock_run.called


@patch("subprocess.run")
def test_marimushka_command_subprocess_failure(mock_run, tmp_path, monkeypatch):
    """Test marimushka command when subprocess fails."""
    monkeypatch.chdir(tmp_path)

    # Create marimo folder with a Python file
    marimo_folder = tmp_path / "book" / "marimo"
    marimo_folder.mkdir(parents=True)
    (marimo_folder / "notebook.py").write_text("# test notebook")

    # Create bin directory
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "uv").touch()
    (bin_dir / "uvx").touch()

    # Mock subprocess.run to simulate failure
    mock_run.return_value = MagicMock(returncode=1, stderr="Error occurred", stdout="")

    with pytest.raises(Exit) as exc_info:
        marimushka_command(
            marimo_folder="book/marimo",
            output="_marimushka",
            uv_bin=str(bin_dir / "uv"),
            uvx_bin=str(bin_dir / "uvx"),
        )

    assert exc_info.value.exit_code == 1
