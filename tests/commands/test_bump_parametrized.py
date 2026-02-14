"""Parametrized tests for bump command demonstrating multi-language support."""

import subprocess
from pathlib import Path

import pytest

from rhiza_tools.commands.bump import BumpOptions, Language, bump_command, get_current_version


@pytest.fixture
def python_project(tmp_path, monkeypatch):
    """Create a temporary Python project."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    # Initialize git
    git = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run([git, "init"], check=True, capture_output=True)
    subprocess.run([git, "config", "user.email", "test@example.com"], check=True, capture_output=True)
    subprocess.run([git, "config", "user.name", "Test User"], check=True, capture_output=True)

    # Create pyproject.toml
    pyproject_content = """[project]
name = "test-project"
version = "0.1.0"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    # Create bumpversion config
    rhiza_dir = tmp_path / ".rhiza"
    rhiza_dir.mkdir(exist_ok=True)
    config_content = """
[tool.bumpversion]
parse = "(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)"
serialize = ["{major}.{minor}.{patch}"]
search = "{current_version}"
replace = "{new_version}"
regex = false
tag = false
commit = false

[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'version = "{current_version}"'
replace = 'version = "{new_version}"'
"""
    (rhiza_dir / ".cfg.toml").write_text(config_content)

    # Commit
    subprocess.run([git, "add", "."], check=True, capture_output=True)
    subprocess.run([git, "commit", "-m", "Initial commit"], check=True, capture_output=True)

    return tmp_path, Language.PYTHON


@pytest.fixture
def go_project(tmp_path, monkeypatch):
    """Create a temporary Go project."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    # Initialize git
    git = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run([git, "init"], check=True, capture_output=True)
    subprocess.run([git, "config", "user.email", "test@example.com"], check=True, capture_output=True)
    subprocess.run([git, "config", "user.name", "Test User"], check=True, capture_output=True)

    # Create go.mod
    (tmp_path / "go.mod").write_text("module github.com/example/test\n\ngo 1.23\n")

    # Create VERSION file
    (tmp_path / "VERSION").write_text("0.1.0\n")

    # Create bumpversion config
    rhiza_dir = tmp_path / ".rhiza"
    rhiza_dir.mkdir(exist_ok=True)
    config_content = """
[tool.bumpversion]
parse = "(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)"
serialize = ["{major}.{minor}.{patch}"]
search = "{current_version}"
replace = "{new_version}"
regex = false
tag = false
commit = false

[[tool.bumpversion.files]]
filename = "VERSION"
"""
    (rhiza_dir / ".cfg.toml").write_text(config_content)

    # Commit
    subprocess.run([git, "add", "."], check=True, capture_output=True)
    subprocess.run([git, "commit", "-m", "Initial commit"], check=True, capture_output=True)

    return tmp_path, Language.GO


@pytest.fixture(params=["python_project", "go_project"])
def multi_language_project(request):
    """Parametrized fixture that provides both Python and Go projects."""
    return request.getfixturevalue(request.param)


class TestBumpMultiLanguage:
    """Parametrized tests that run against both Python and Go projects."""

    def test_bump_patch(self, multi_language_project):
        """Test patch bump works for all supported languages."""
        _project_path, language = multi_language_project
        bump_command(BumpOptions(version="patch", language=language))
        assert get_current_version(language) == "0.1.1"

    def test_bump_minor(self, multi_language_project):
        """Test minor bump works for all supported languages."""
        _project_path, language = multi_language_project
        bump_command(BumpOptions(version="minor", language=language))
        assert get_current_version(language) == "0.2.0"

    def test_bump_major(self, multi_language_project):
        """Test major bump works for all supported languages."""
        _project_path, language = multi_language_project
        bump_command(BumpOptions(version="major", language=language))
        assert get_current_version(language) == "1.0.0"

    def test_bump_explicit_version(self, multi_language_project):
        """Test explicit version bump works for all supported languages."""
        _project_path, language = multi_language_project
        bump_command(BumpOptions(version="2.3.4", language=language))
        assert get_current_version(language) == "2.3.4"


class TestLanguageDetection:
    """Tests for language auto-detection."""

    def test_detect_python(self, python_project):
        """Test Python project detection."""
        _project_path, language = python_project
        assert Language.detect() == Language.PYTHON

    def test_detect_go(self, go_project):
        """Test Go project detection."""
        _project_path, language = go_project
        assert Language.detect() == Language.GO

    def test_detect_none(self, tmp_path, monkeypatch):
        """Test detection returns None when no supported files exist."""
        monkeypatch.chdir(tmp_path)
        assert Language.detect() is None
