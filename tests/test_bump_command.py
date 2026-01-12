"""Tests for the bump command."""

import os

import pytest
import tomlkit
import typer

from rhiza_tools.commands.bump import (
    bump_command,
    get_current_version,
)


@pytest.fixture
def bump_project(temp_project):
    """Create a project with bumpversion config."""
    rhiza_dir = temp_project / ".rhiza"
    rhiza_dir.mkdir(exist_ok=True)

    config_content = """
[tool.bumpversion]
parse = "(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)(?:-(?P<release>[a-z]+)\\\\.(?P<pre_n>\\\\d+))?(?:\\\\+build\\\\.(?P<build_n>\\\\d+))?"
serialize = [
    "{major}.{minor}.{patch}-{release}.{pre_n}+build.{build_n}",
    "{major}.{minor}.{patch}+build.{build_n}",
    "{major}.{minor}.{patch}-{release}.{pre_n}",
    "{major}.{minor}.{patch}"
]
search = "{current_version}"
replace = "{new_version}"
regex = false
ignore_missing_version = false
tag = false
commit = false

[tool.bumpversion.parts.release]
optional_value = "prod"
values = [
    "dev",
    "alpha",
    "beta",
    "rc",
    "prod"
]

[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'version = "{current_version}"'
replace = 'version = "{new_version}"'
"""  # noqa: E501
    with open(rhiza_dir / ".cfg.toml", "w") as f:
        f.write(config_content)

    return temp_project


def test_bump_patch(bump_project):
    """Test bumping the patch version."""
    bump_command(version="patch")
    assert get_current_version() == "0.1.1"


def test_bump_minor(bump_project):
    """Test bumping the minor version."""
    bump_command(version="minor")
    assert get_current_version() == "0.2.0"


def test_bump_major(bump_project):
    """Test bumping the major version."""
    bump_command(version="major")
    assert get_current_version() == "1.0.0"


def test_bump_explicit_version(bump_project):
    """Test bumping to an explicit version."""
    bump_command(version="1.2.3")
    assert get_current_version() == "1.2.3"


def test_bump_explicit_version_with_v_prefix(bump_project):
    """Test bumping to an explicit version with 'v' prefix."""
    bump_command(version="v1.2.3")
    assert get_current_version() == "1.2.3"


def test_dry_run(bump_project):
    """Test dry run does not change the version."""
    bump_command(version="patch", dry_run=True)
    assert get_current_version() == "0.1.0"


def test_invalid_version(bump_project):
    """Test that invalid versions raise an error."""
    with pytest.raises(typer.Exit):
        bump_command(version="invalid")


def test_missing_pyproject_toml(bump_project):
    """Test that missing pyproject.toml raises an error."""
    os.remove("pyproject.toml")
    with pytest.raises(typer.Exit):
        bump_command(version="patch")


def test_bump_prerelease(bump_project):
    """Test bumping prerelease."""
    # First bump to a prerelease version
    bump_command(version="0.1.0-alpha.1")
    assert get_current_version() == "0.1.0-alpha.1"

    # Bump prerelease
    bump_command(version="prerelease")
    assert get_current_version() == "0.1.0-alpha.2"


def test_bump_build(bump_project):
    """Test bumping build."""
    # First bump to a build version
    bump_command(version="0.1.0+build.1")
    assert get_current_version() == "0.1.0+build.1"

    # Bump build
    bump_command(version="build")
    assert get_current_version() == "0.1.0+build.2"


def test_bump_interactive_patch(bump_project, monkeypatch):
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


def test_bump_interactive_minor(bump_project, monkeypatch):
    """Test interactive bump selection (Minor)."""

    class MockQuestion:
        def ask(self):
            return "Minor (0.1.0 -> 0.2.0)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.2.0"


def test_bump_interactive_cancel(bump_project, monkeypatch):
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


def test_bump_alpha_argument(bump_project):
    """Test bumping alpha version via argument."""
    bump_command(version="alpha")
    assert get_current_version() == "0.1.1-alpha.1"

    bump_command(version="alpha")
    assert get_current_version() == "0.1.1-alpha.2"


def test_bump_beta_argument(bump_project):
    """Test bumping beta version via argument."""
    bump_command(version="beta")
    assert get_current_version() == "0.1.1-beta.1"


def test_bump_dev_argument(bump_project):
    """Test bumping dev version via argument."""
    bump_command(version="dev")
    assert get_current_version() == "0.1.1-dev.1"


def test_bump_rc_argument(bump_project):
    """Test bumping rc version via argument."""
    bump_command(version="rc")
    assert get_current_version() == "0.1.1-rc.1"


def test_bump_prerelease_transition(bump_project):
    """Test transitioning between prerelease types."""
    # Start with alpha
    bump_command(version="alpha")
    assert get_current_version() == "0.1.1-alpha.1"

    # Switch to beta
    bump_command(version="beta")
    assert get_current_version() == "0.1.1-beta.1"

    # Switch back to alpha (should bump patch and start new alpha)
    # 0.1.1-beta.1 -> alpha -> 0.1.1-alpha.1
    bump_command(version="alpha")
    assert get_current_version() == "0.1.1-alpha.1"


def test_bump_interactive_rc(bump_project, monkeypatch):
    """Test interactive bump selection (RC)."""

    class MockQuestion:
        def ask(self):
            return "RC (0.1.0 -> 0.1.1-rc.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.1-rc.1"


def test_bump_interactive_build(bump_project, monkeypatch):
    """Test interactive bump selection (Build)."""

    class MockQuestion:
        def ask(self):
            return "Build (0.1.0 -> 0.1.0+build.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.0+build.1"


def test_get_current_version_error_handling(bump_project, monkeypatch):
    """Test error handling when reading version from pyproject.toml fails."""

    def mock_open_error(*args, **kwargs):
        raise OSError("File read error")

    monkeypatch.setattr("builtins.open", mock_open_error)

    with pytest.raises(typer.Exit) as excinfo:
        get_current_version()
    assert excinfo.value.exit_code == 1


def test_bump_invalid_semantic_version_in_pyproject(bump_project):
    """Test error handling when pyproject.toml has invalid semantic version."""
    # Update pyproject.toml with invalid version
    with open("pyproject.toml") as f:
        data = tomlkit.parse(f.read())

    data["project"]["version"] = "not-a-valid-semver"

    with open("pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(data))

    with pytest.raises(typer.Exit) as excinfo:
        bump_command(version="patch")
    assert excinfo.value.exit_code == 1


def test_bump_interactive_alpha(bump_project, monkeypatch):
    """Test interactive bump selection (Alpha)."""

    class MockQuestion:
        def ask(self):
            return "Alpha (0.1.0 -> 0.1.1-alpha.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.1-alpha.1"


def test_bump_interactive_beta(bump_project, monkeypatch):
    """Test interactive bump selection (Beta)."""

    class MockQuestion:
        def ask(self):
            return "Beta (0.1.0 -> 0.1.1-beta.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.1-beta.1"


def test_bump_interactive_dev(bump_project, monkeypatch):
    """Test interactive bump selection (Dev)."""

    class MockQuestion:
        def ask(self):
            return "Dev (0.1.0 -> 0.1.1-dev.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    bump_command(version=None)
    assert get_current_version() == "0.1.1-dev.1"


def test_bump_interactive_prerelease(bump_project, monkeypatch):
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


def test_bump_interactive_major(bump_project, monkeypatch):
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

    # _parse_version_argument(version, current_version_str)
    result = _parse_version_argument(None, "0.1.0")
    assert result == ""


def test_determine_bump_type_from_choice_no_match():
    """Test _determine_bump_type_from_choice when no prefix matches."""
    from rhiza_tools.commands.bump import _determine_bump_type_from_choice

    # Test with a string that doesn't match any prefix
    result = _determine_bump_type_from_choice("Unknown choice string")
    assert result == ""


def test_determine_bump_type_from_choice_with_match():
    """Test _determine_bump_type_from_choice when a prefix matches."""
    from rhiza_tools.commands.bump import _determine_bump_type_from_choice

    # Test with strings that match prefixes
    assert _determine_bump_type_from_choice("Patch (0.1.0 -> 0.1.1)") == "patch"
    assert _determine_bump_type_from_choice("Minor (0.1.0 -> 0.2.0)") == "minor"
    assert _determine_bump_type_from_choice("Major (0.1.0 -> 1.0.0)") == "major"
    assert _determine_bump_type_from_choice("Alpha (0.1.0 -> 0.1.1-alpha.1)") == "alpha"
    assert _determine_bump_type_from_choice("Beta (0.1.0 -> 0.1.1-beta.1)") == "beta"
    assert _determine_bump_type_from_choice("RC (0.1.0 -> 0.1.1-rc.1)") == "rc"
    assert _determine_bump_type_from_choice("Dev (0.1.0 -> 0.1.1-dev.1)") == "dev"
    assert _determine_bump_type_from_choice("Prerelease (0.1.0-alpha.1 -> 0.1.0-alpha.2)") == "prerelease"
    assert _determine_bump_type_from_choice("Build (0.1.0 -> 0.1.0+build.1)") == "build"


def test_bump_interactive_invalid_semver_in_config(bump_project, monkeypatch):
    """Test interactive bump when config has invalid semantic version."""
    # Update pyproject.toml with invalid version for interactive mode
    with open("pyproject.toml") as f:
        data = tomlkit.parse(f.read())

    data["project"]["version"] = "invalid-version"

    with open("pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(data))

    # Mock interactive prompt - though it should fail before reaching it
    class MockQuestion:
        def ask(self):
            return "Patch (invalid-version -> 0.1.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)

    # Should fail with exit code 1 due to invalid semver
    with pytest.raises(typer.Exit) as excinfo:
        bump_command(version=None)
    assert excinfo.value.exit_code == 1


def test_bump_with_allow_dirty_flag(bump_project, monkeypatch):
    """Test bump command with allow_dirty flag."""
    # Create a modified file to make the repo dirty
    with open("test_file.txt", "w") as f:
        f.write("test")

    # Mock get_configuration to verify allow_dirty is passed
    called_with_params = {}

    def mock_get_config(*args, **kwargs):
        called_with_params.update(kwargs)
        # Import the real function to get a real config
        from bumpversion.config import get_configuration as real_get_config

        return real_get_config(*args, **kwargs)

    monkeypatch.setattr("rhiza_tools.commands.bump.get_configuration", mock_get_config)

    # Test with allow_dirty=True
    bump_command(version="patch", allow_dirty=True)
    assert called_with_params.get("allow_dirty") is True


def test_bump_with_commit_flag(bump_project, monkeypatch):
    """Test bump command with commit flag."""
    # Mock get_configuration to verify commit flag is passed
    called_with_params = {}

    def mock_get_config(*args, **kwargs):
        called_with_params.update(kwargs)
        # Import the real function to get a real config
        from bumpversion.config import get_configuration as real_get_config

        return real_get_config(*args, **kwargs)

    monkeypatch.setattr("rhiza_tools.commands.bump.get_configuration", mock_get_config)

    # Test with commit=True
    bump_command(version="patch", commit=True)
    assert called_with_params.get("commit") is True


def test_bump_configuration_load_failure(bump_project, monkeypatch):
    """Test bump command when configuration loading fails."""

    def mock_get_config(*args, **kwargs):
        raise Exception("Configuration load error")

    monkeypatch.setattr("rhiza_tools.commands.bump.get_configuration", mock_get_config)

    # Should fail with exit code 1
    with pytest.raises(typer.Exit) as excinfo:
        bump_command(version="patch")
    assert excinfo.value.exit_code == 1


def test_bump_operation_failure(bump_project, monkeypatch):
    """Test bump command when the bump operation fails."""

    def mock_do_bump(*args, **kwargs):
        raise Exception("Bump operation failed")

    monkeypatch.setattr("rhiza_tools.commands.bump.do_bump", mock_do_bump)

    # Should fail with exit code 1
    with pytest.raises(typer.Exit) as excinfo:
        bump_command(version="patch")
    assert excinfo.value.exit_code == 1
