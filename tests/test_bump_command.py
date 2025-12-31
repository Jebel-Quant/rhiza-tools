"""Tests for the bump command."""

import os

import pytest
import typer

from rhiza_tools.commands.bump import (
    bump_command,
    get_current_version,
    update_version,
)


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


def test_get_current_version_error_handling(temp_project, monkeypatch):
    """Test error handling when reading version from pyproject.toml fails."""

    def mock_open_error(*args, **kwargs):
        raise OSError("File read error")

    monkeypatch.setattr("builtins.open", mock_open_error)

    with pytest.raises(typer.Exit) as excinfo:
        get_current_version()
    assert excinfo.value.exit_code == 1


def test_update_version_error_handling(temp_project, monkeypatch):
    """Test error handling when updating version in pyproject.toml fails."""
    # Mock open to fail on write operations
    original_open = open

    def mock_open_fail_on_write(file, mode="r", *args, **kwargs):
        if "w" in mode:
            raise OSError("File write error")
        return original_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", mock_open_fail_on_write)

    with pytest.raises(typer.Exit) as excinfo:
        update_version("1.0.0")
    assert excinfo.value.exit_code == 1


def test_bump_invalid_semantic_version_in_pyproject(temp_project):
    """Test error handling when pyproject.toml has invalid semantic version."""
    # Update pyproject.toml with invalid version
    import tomlkit

    with open("pyproject.toml") as f:
        data = tomlkit.parse(f.read())

    data["project"]["version"] = "not-a-valid-semver"

    with open("pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(data))

    with pytest.raises(typer.Exit) as excinfo:
        bump_command(version="patch")
    assert excinfo.value.exit_code == 1


def test_bump_version_verification_failure(temp_project, monkeypatch):
    """Test error handling when version verification after update fails."""
    # Mock get_current_version to return different values on subsequent calls
    # First call returns initial version, second returns incorrect version to simulate verification failure
    # (Expected new version after patch bump would be 0.1.1, but we return 0.9.9 to test error handling)
    versions = iter(["0.1.0", "0.9.9"])

    def mock_get_current_version():
        return next(versions)

    monkeypatch.setattr("rhiza_tools.commands.bump.get_current_version", mock_get_current_version)

    with pytest.raises(typer.Exit) as excinfo:
        bump_command(version="patch")
    assert excinfo.value.exit_code == 1


def test_bump_interactive_alpha(temp_project, monkeypatch):
    """Test interactive bump selection (Alpha)."""

    class MockQuestion:
        def ask(self):
            return "Alpha (0.1.0 -> 0.1.1-alpha.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.1-alpha.1"


def test_bump_interactive_beta(temp_project, monkeypatch):
    """Test interactive bump selection (Beta)."""

    class MockQuestion:
        def ask(self):
            return "Beta (0.1.0 -> 0.1.1-beta.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.1-beta.1"


def test_bump_interactive_dev(temp_project, monkeypatch):
    """Test interactive bump selection (Dev)."""

    class MockQuestion:
        def ask(self):
            return "Dev (0.1.0 -> 0.1.1-dev.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.1-dev.1"


def test_bump_interactive_prerelease(temp_project, monkeypatch):
    """Test interactive bump selection (Prerelease)."""
    # First set up a prerelease version
    bump_command(version="0.1.0-alpha.1")

    class MockQuestion:
        def ask(self):
            return "Prerelease (0.1.0-alpha.1 -> 0.1.0-alpha.2)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.0-alpha.2"


def test_bump_interactive_major(temp_project, monkeypatch):
    """Test interactive bump selection (Major)."""

    class MockQuestion:
        def ask(self):
            return "Major (0.1.0 -> 1.0.0)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "1.0.0"


def test_parse_version_argument_none():
    """Test _parse_version_argument with None."""
    from rhiza_tools.commands.bump import _parse_version_argument

    bump_type, explicit_version = _parse_version_argument(None)
    assert bump_type == ""
    assert explicit_version == ""


def test_determine_bump_type_from_choice_no_match():
    """Test _determine_bump_type_from_choice when no prefix matches."""
    from rhiza_tools.commands.bump import _determine_bump_type_from_choice

    # Test with a string that doesn't match any prefix
    result = _determine_bump_type_from_choice("Unknown choice string")
    assert result == ""


def test_calculate_new_version_unknown_bump_type(temp_project):
    """Test _calculate_new_version with unknown bump type."""
    import semver

    from rhiza_tools.commands.bump import _calculate_new_version

    current_version = semver.Version.parse("0.1.0")

    with pytest.raises(typer.Exit) as excinfo:
        _calculate_new_version(current_version, "unknown_type", "")
    assert excinfo.value.exit_code == 1


def test_calculate_new_version_no_bump_or_version(temp_project):
    """Test _calculate_new_version with no bump type or explicit version."""
    import semver

    from rhiza_tools.commands.bump import _calculate_new_version

    current_version = semver.Version.parse("0.1.0")

    with pytest.raises(typer.Exit) as excinfo:
        _calculate_new_version(current_version, "", "")
    assert excinfo.value.exit_code == 1
