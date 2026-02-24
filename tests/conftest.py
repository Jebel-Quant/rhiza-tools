"""Pytest configuration and fixtures for the tests directory.

Security Notes:
- S101 (assert usage): Asserts are appropriate in test code for validating conditions
- S603 (subprocess without shell=True): All subprocess calls use lists of known commands (git),
  not user input, making them safe from shell injection
- S607 (subprocess with partial path): Using 'git' from PATH is acceptable in test fixtures
  as the test environment is controlled and git is a required development dependency
"""

import subprocess

import pytest

# Get absolute path for git executable
GIT = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def temp_project(tmp_path, monkeypatch):
    """Create a temporary project directory with git and pyproject.toml.

    This fixture:
    - Creates a temporary directory
    - Initializes a git repository
    - Creates a pyproject.toml with version 0.1.0
    - Changes working directory to the temp project
    - Returns the path to the temporary project
    """
    # Change to temporary directory
    monkeypatch.chdir(tmp_path)

    # Prevent git from walking up to the real repo if anything goes wrong
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    # Initialize git repository
    subprocess.run([GIT, "init"], check=True, capture_output=True)
    subprocess.run([GIT, "config", "user.email", "test@example.com"], check=True, capture_output=True)
    subprocess.run([GIT, "config", "user.name", "Test User"], check=True, capture_output=True)

    # Create pyproject.toml with initial version
    pyproject_content = """[project]
name = "test-project"
version = "0.1.0"
"""
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(pyproject_content)

    # Commit the initial state
    subprocess.run([GIT, "add", "."], check=True, capture_output=True)
    subprocess.run([GIT, "commit", "-m", "Initial commit"], check=True, capture_output=True)

    return tmp_path
