"""Tests for the update-readme Python command."""

from unittest.mock import Mock, patch

import pytest
import typer

from rhiza_tools.commands.update_readme import (
    _get_make_help_output,
    _update_readme_with_help,
    update_readme_command,
)


def test_update_readme_success(tmp_path, monkeypatch):
    """Test successful update of README.md with help output."""
    monkeypatch.chdir(tmp_path)
    readme_path = tmp_path / "README.md"

    # Create a README with the target section
    initial_content = """# Project

Some description.

Run `make help` to see all available targets:

```makefile
old help content
```

Footer content.
"""
    readme_path.write_text(initial_content)

    help_output = "New help output\nwith multiple lines"

    # Update the README
    result = _update_readme_with_help(readme_path, help_output)

    assert result is True

    # Verify content
    new_content = readme_path.read_text()
    assert "New help output" in new_content
    assert "with multiple lines" in new_content
    assert "old help content" not in new_content
    assert "Footer content" in new_content


def test_update_readme_with_help_no_marker(tmp_path, monkeypatch):
    """Test behavior when README.md lacks the marker."""
    monkeypatch.chdir(tmp_path)
    readme_path = tmp_path / "README.md"

    # Create a README without the target section
    initial_content = """# Project

No help section here.
"""
    readme_path.write_text(initial_content)

    help_output = "Some help output"

    # Update should return False
    result = _update_readme_with_help(readme_path, help_output)

    assert result is False

    # Verify content is unchanged
    assert readme_path.read_text() == initial_content


def test_update_readme_with_help_preserves_surrounding_content(tmp_path, monkeypatch):
    """Test that content before and after the help block is preserved."""
    monkeypatch.chdir(tmp_path)
    readme_path = tmp_path / "README.md"

    initial_content = """Header

Run `make help` to see all available targets:

```makefile
replace me
```

Footer
"""
    readme_path.write_text(initial_content)

    help_output = "Replaced content"

    result = _update_readme_with_help(readme_path, help_output)

    assert result is True

    new_content = readme_path.read_text()
    assert new_content.startswith("Header\n\nRun `make help`")
    assert new_content.endswith("```\n\nFooter\n")
    assert "Replaced content" in new_content
    assert "replace me" not in new_content


def test_update_readme_help_command_no_readme(tmp_path, monkeypatch):
    """Test the command when README.md doesn't exist."""
    monkeypatch.chdir(tmp_path)

    # Run the command - should exit with error
    with pytest.raises(typer.Exit) as exc_info:
        update_readme_command(dry_run=False)

    assert exc_info.value.exit_code == 1


def test_get_make_help_output_success():
    """Test _get_make_help_output successfully runs make help and processes output."""
    mock_result = Mock()
    mock_result.stdout = (
        "\x1b[36mHelp:\x1b[0m\nmake[1]: Entering directory\ntarget1: description\nmake[1]: Leaving directory"
    )

    with patch("subprocess.run", return_value=mock_result):
        output = _get_make_help_output()

    # ANSI codes should be stripped
    assert "\x1b[36m" not in output
    assert "\x1b[0m" not in output
    # Directory messages should be filtered
    assert "Entering directory" not in output
    assert "Leaving directory" not in output
    assert "make[1]" not in output
    # Content should be preserved
    assert "Help:" in output
    assert "target1: description" in output


def test_get_make_help_output_make_not_found():
    """Test _get_make_help_output handles make command not found."""
    with patch("subprocess.run", side_effect=FileNotFoundError()):
        with pytest.raises(typer.Exit) as exc_info:
            _get_make_help_output()
        assert exc_info.value.exit_code == 1


def test_get_make_help_output_subprocess_error():
    """Test _get_make_help_output handles other subprocess errors."""
    with patch("subprocess.run", side_effect=Exception("Test error")):
        with pytest.raises(typer.Exit) as exc_info:
            _get_make_help_output()
        assert exc_info.value.exit_code == 1


def test_update_readme_command_dry_run(tmp_path, monkeypatch):
    """Test the command with dry_run=True doesn't modify README."""
    monkeypatch.chdir(tmp_path)
    readme_path = tmp_path / "README.md"

    # Create a README with the target section
    initial_content = """# Project

Run `make help` to see all available targets:

```makefile
old content
```

Footer.
"""
    readme_path.write_text(initial_content)

    # Mock make help output
    mock_result = Mock()
    mock_result.stdout = "New help output"

    with patch("subprocess.run", return_value=mock_result):
        # Run the command in dry-run mode
        update_readme_command(dry_run=True)

    # Verify content was NOT updated
    new_content = readme_path.read_text()
    assert new_content == initial_content
    assert "old content" in new_content
    assert "New help output" not in new_content


def test_update_readme_marker_without_code_fence(tmp_path, monkeypatch):
    """Test behavior when marker is found but no code fence follows."""
    monkeypatch.chdir(tmp_path)
    readme_path = tmp_path / "README.md"

    # Create a README with marker but no code fence
    initial_content = """# Project

Run `make help` to see all available targets:

Some other content here.
"""
    readme_path.write_text(initial_content)

    help_output = "New help output"

    # Update should return False
    result = _update_readme_with_help(readme_path, help_output)

    assert result is False

    # Verify content is unchanged
    assert readme_path.read_text() == initial_content


def test_update_readme_with_help_read_error(tmp_path):
    """Test _update_readme_with_help handles read errors other than FileNotFoundError."""
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# Test")

    # Mock Path.read_text to raise a generic exception
    with patch("pathlib.Path.read_text", side_effect=PermissionError("Permission denied")):
        with pytest.raises(typer.Exit) as exc_info:
            _update_readme_with_help(readme_path, "help output")
        assert exc_info.value.exit_code == 1


def test_update_readme_with_help_file_not_found(tmp_path):
    """Test _update_readme_with_help handles FileNotFoundError."""
    readme_path = tmp_path / "nonexistent_file.md"

    # Try to update a non-existent file
    with pytest.raises(typer.Exit) as exc_info:
        _update_readme_with_help(readme_path, "help output")
    assert exc_info.value.exit_code == 1


def test_update_readme_with_help_write_error(tmp_path):
    """Test _update_readme_with_help handles write errors."""
    from pathlib import Path

    readme_path = tmp_path / "README.md"

    # Create a README with the target section
    initial_content = """# Project

Run `make help` to see all available targets:

```makefile
old help content
```

Footer content.
"""
    readme_path.write_text(initial_content)

    help_output = "New help output"

    # We need to mock write_text but allow read_text to work normally
    original_read = Path.read_text

    def mock_write(*args, **kwargs):
        raise PermissionError("Permission denied")  # noqa: TRY003

    with patch("pathlib.Path.write_text", mock_write), patch("pathlib.Path.read_text", original_read):
        with pytest.raises(typer.Exit) as exc_info:
            _update_readme_with_help(readme_path, help_output)
        assert exc_info.value.exit_code == 1


def test_update_readme_command_successful_update(tmp_path, monkeypatch):
    """Test the command successfully updates README.md."""
    monkeypatch.chdir(tmp_path)
    readme_path = tmp_path / "README.md"

    # Create a README with the target section
    initial_content = """# Project

Run `make help` to see all available targets:

```makefile
old content
```

Footer.
"""
    readme_path.write_text(initial_content)

    # Mock make help output
    mock_result = Mock()
    mock_result.stdout = "New help output from make"

    with patch("subprocess.run", return_value=mock_result):
        # Run the command
        update_readme_command(dry_run=False)

    # Verify content was updated
    new_content = readme_path.read_text()
    assert "New help output from make" in new_content
    assert "old content" not in new_content


def test_update_readme_command_no_marker_found(tmp_path, monkeypatch):
    """Test the command when README has no marker."""
    monkeypatch.chdir(tmp_path)
    readme_path = tmp_path / "README.md"

    # Create a README without the marker
    initial_content = """# Project

No help section here.
"""
    readme_path.write_text(initial_content)

    # Mock make help output
    mock_result = Mock()
    mock_result.stdout = "New help output"

    with patch("subprocess.run", return_value=mock_result):
        # Run the command - should not fail but also not update
        update_readme_command(dry_run=False)

    # Verify content was NOT updated
    new_content = readme_path.read_text()
    assert new_content == initial_content
