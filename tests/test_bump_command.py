"""Tests for the bump command."""

import pytest
import typer

from rhiza_tools.commands.bump import bump_command, get_current_version


def test_bump_patch(temp_project):
    """Test bumping the patch version."""
    bump_command(version="patch")
    assert get_current_version() == "0.1.1"


def test_bump_minor(temp_project):
    """Test bumping the minor version."""
    bump_command(version="minor")
    assert get_current_version() == "0.2.0"


def test_bump_major(temp_project):
    """Test bumping the major version."""
    bump_command(version="major")
    assert get_current_version() == "1.0.0"


def test_bump_explicit_version(temp_project):
    """Test bumping to an explicit version."""
    bump_command(version="1.2.3")
    assert get_current_version() == "1.2.3"


def test_bump_explicit_version_with_v_prefix(temp_project):
    """Test bumping to an explicit version with 'v' prefix."""
    bump_command(version="v1.2.3")
    assert get_current_version() == "1.2.3"


def test_dry_run(temp_project):
    """Test dry run does not change the version."""
    bump_command(version="patch", dry_run=True)
    assert get_current_version() == "0.1.0"


def test_invalid_version(temp_project):
    """Test that invalid versions raise an error."""
    with pytest.raises(typer.Exit):
        bump_command(version="invalid")


def test_missing_pyproject_toml(temp_project):
    """Test that missing pyproject.toml raises an error."""
    import os

    os.remove("pyproject.toml")
    with pytest.raises(typer.Exit):
        bump_command(version="patch")


def test_bump_prerelease(temp_project):
    """Test bumping prerelease."""
    # First bump to a prerelease version
    bump_command(version="0.1.0-alpha.1")
    assert get_current_version() == "0.1.0-alpha.1"

    # Bump prerelease
    bump_command(version="prerelease")
    assert get_current_version() == "0.1.0-alpha.2"


def test_bump_build(temp_project):
    """Test bumping build."""
    # First bump to a build version
    bump_command(version="0.1.0+build.1")
    assert get_current_version() == "0.1.0+build.1"

    # Bump build
    bump_command(version="build")
    assert get_current_version() == "0.1.0+build.2"


def test_bump_interactive_patch(temp_project, monkeypatch):
    """Test interactive bump selection (Patch)."""

    # Mock the return value of qs.select(...).ask()
    class MockQuestion:
        def ask(self):
            return "Patch (0.1.0 -> 0.1.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.1"


def test_bump_interactive_minor(temp_project, monkeypatch):
    """Test interactive bump selection (Minor)."""

    class MockQuestion:
        def ask(self):
            return "Minor (0.1.0 -> 0.2.0)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.2.0"


def test_bump_interactive_cancel(temp_project, monkeypatch):
    """Test interactive bump cancellation."""

    class MockQuestion:
        def ask(self):
            return None

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    # Should exit with code 0 if cancelled
    with pytest.raises(typer.Exit) as excinfo:
        bump_command(version=None)

    assert excinfo.value.exit_code == 0
    assert get_current_version() == "0.1.0"


def test_bump_alpha_argument(temp_project):
    """Test bumping alpha version via argument."""
    bump_command(version="alpha")
    assert get_current_version() == "0.1.1-alpha.1"

    bump_command(version="alpha")
    assert get_current_version() == "0.1.1-alpha.2"


def test_bump_beta_argument(temp_project):
    """Test bumping beta version via argument."""
    bump_command(version="beta")
    assert get_current_version() == "0.1.1-beta.1"


def test_bump_dev_argument(temp_project):
    """Test bumping dev version via argument."""
    bump_command(version="dev")
    assert get_current_version() == "0.1.1-dev.1"


def test_bump_rc_argument(temp_project):
    """Test bumping rc version via argument."""
    bump_command(version="rc")
    assert get_current_version() == "0.1.1-rc.1"


def test_bump_prerelease_transition(temp_project):
    """Test transitioning between prerelease types."""
    # Start with alpha
    bump_command(version="alpha")
    assert get_current_version() == "0.1.1-alpha.1"

    # Switch to beta
    bump_command(version="beta")
    assert get_current_version() == "0.1.1-beta.1"

    # Switch to rc (via interactive since rc arg is not supported yet)
    # But wait, rc is not in the allowed args list in bump.py
    # So we can't test it via argument.

    # Switch back to alpha (should bump patch and start new alpha)
    # Wait, get_next_prerelease logic:
    # if current_version.prerelease:
    #     if current_version.prerelease.startswith(token):
    #         return current_version.bump_prerelease()
    #     else:
    #         return current_version.replace(prerelease=f"{token}.1")

    # So 0.1.1-beta.1 -> alpha -> 0.1.1-alpha.1
    bump_command(version="alpha")
    assert get_current_version() == "0.1.1-alpha.1"


def test_bump_interactive_rc(temp_project, monkeypatch):
    """Test interactive bump selection (RC)."""

    class MockQuestion:
        def ask(self):
            return "RC (0.1.0 -> 0.1.1-rc.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.1-rc.1"


def test_bump_interactive_build(temp_project, monkeypatch):
    """Test interactive bump selection (Build)."""

    class MockQuestion:
        def ask(self):
            return "Build (0.1.0 -> 0.1.0+build.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.0+build.1"
