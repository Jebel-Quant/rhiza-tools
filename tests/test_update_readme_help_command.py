"""Tests for the update-readme-help Python command."""

import pytest
from click.exceptions import Exit

from rhiza_tools.commands.update_readme import (
    _update_readme_with_help,
    update_readme,
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
    with pytest.raises(Exit) as exc_info:
        update_readme(dry_run=False)

    assert exc_info.value.exit_code == 1
