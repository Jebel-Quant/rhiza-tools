"""Tests for the update-readme-help Python command."""

import subprocess
from pathlib import Path

import pytest

from rhiza_tools.commands.update_readme_help import (
    _get_make_help_output,
    _update_readme_with_help,
    update_readme_help_command,
)


def test_get_make_help_output(git_repo, monkeypatch):
    """Test getting help output from make."""
    monkeypatch.chdir(git_repo)
    
    # The git_repo fixture creates a mock make command
    output = _get_make_help_output()
    
    # The mock make script outputs "Mock Makefile Help"
    assert "Mock Makefile Help" in output
    assert "target: ## Description" in output


def test_update_readme_with_help_success(git_repo, monkeypatch):
    """Test successful update of README.md with help output."""
    monkeypatch.chdir(git_repo)
    readme_path = git_repo / "README.md"
    
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


def test_update_readme_with_help_no_marker(git_repo, monkeypatch):
    """Test behavior when README.md lacks the marker."""
    monkeypatch.chdir(git_repo)
    readme_path = git_repo / "README.md"
    
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


def test_update_readme_with_help_preserves_surrounding_content(git_repo, monkeypatch):
    """Test that content before and after the help block is preserved."""
    monkeypatch.chdir(git_repo)
    readme_path = git_repo / "README.md"
    
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


def test_update_readme_help_command_integration(git_repo, monkeypatch):
    """Test the full command integration."""
    monkeypatch.chdir(git_repo)
    readme_path = git_repo / "README.md"
    
    # Create a README with the target section
    initial_content = """# Project

Run `make help` to see all available targets:

```makefile
old content
```

Footer.
"""
    readme_path.write_text(initial_content)
    
    # Run the command
    update_readme_help_command(dry_run=False)
    
    # Verify content was updated
    new_content = readme_path.read_text()
    assert "Mock Makefile Help" in new_content
    assert "old content" not in new_content
    assert "Footer" in new_content


def test_update_readme_help_command_dry_run(git_repo, monkeypatch):
    """Test the command with dry_run=True."""
    monkeypatch.chdir(git_repo)
    readme_path = git_repo / "README.md"
    
    # Create a README with the target section
    initial_content = """# Project

Run `make help` to see all available targets:

```makefile
old content
```

Footer.
"""
    readme_path.write_text(initial_content)
    
    # Run the command in dry-run mode
    update_readme_help_command(dry_run=True)
    
    # Verify content was NOT updated
    new_content = readme_path.read_text()
    assert new_content == initial_content


def test_update_readme_help_command_no_readme(tmp_path, monkeypatch):
    """Test the command when README.md doesn't exist."""
    monkeypatch.chdir(tmp_path)
    
    # Run the command - should exit with error
    with pytest.raises(SystemExit) as exc_info:
        update_readme_help_command(dry_run=False)
    
    assert exc_info.value.code == 1
