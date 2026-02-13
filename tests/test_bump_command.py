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

    # Commit the config file to git so tests with commit=True can work
    import subprocess

    git = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run([git, "add", ".rhiza/.cfg.toml"], check=True, capture_output=True)
    subprocess.run([git, "commit", "-m", "Add bumpversion config"], check=True, capture_output=True)

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
        raise OSError("File read error")  # noqa: TRY003

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
        raise Exception("Configuration load error")  # noqa: TRY002, TRY003

    monkeypatch.setattr("rhiza_tools.commands.bump.get_configuration", mock_get_config)

    # Should fail with exit code 1
    with pytest.raises(typer.Exit) as excinfo:
        bump_command(version="patch")
    assert excinfo.value.exit_code == 1


def test_bump_operation_failure(bump_project, monkeypatch):
    """Test bump command when the bump operation fails."""

    def mock_do_bump(*args, **kwargs):
        raise Exception("Bump operation failed")  # noqa: TRY002, TRY003

    monkeypatch.setattr("rhiza_tools.commands.bump.do_bump", mock_do_bump)

    # Should fail with exit code 1
    with pytest.raises(typer.Exit) as excinfo:
        bump_command(version="patch")
    assert excinfo.value.exit_code == 1


def test_bump_with_push_flag(bump_project):
    """Test bump command with push flag."""
    from unittest.mock import MagicMock, patch

    # Mock _handle_push_to_remote to avoid real git push
    mock_push = MagicMock()
    with patch("rhiza_tools.commands.bump._handle_push_to_remote", mock_push):
        bump_command(version="patch", push=True)

    assert get_current_version() == "0.1.1"
    mock_push.assert_called_once()


def test_bump_with_branch_flag(bump_project):
    """Test bump command with branch flag."""
    from unittest.mock import MagicMock, patch

    # Mock branch checkout/restore to avoid real git branch operations
    mock_checkout = MagicMock(return_value="original-branch")
    mock_restore = MagicMock()

    with patch("rhiza_tools.commands.bump._handle_branch_checkout", mock_checkout):
        with patch("rhiza_tools.commands.bump._restore_original_branch", mock_restore):
            bump_command(version="patch", branch="test-branch")

    assert get_current_version() == "0.1.1"
    mock_checkout.assert_called_once_with("test-branch", False)
    mock_restore.assert_called_once_with("original-branch", False)


def test_bump_push_flag_implies_commit(bump_project):
    """Test that push flag implies commit flag."""
    from unittest.mock import MagicMock, patch

    # Mock _handle_push_to_remote to avoid real git push
    mock_push = MagicMock()
    with patch("rhiza_tools.commands.bump._handle_push_to_remote", mock_push):
        # Call with push=True but commit=False - push should still happen (implies commit)
        bump_command(version="patch", push=True, commit=False)

    assert get_current_version() == "0.1.1"
    mock_push.assert_called_once()


def test_bump_with_push_failure(bump_project):
    """Test bump command when git push fails."""
    from unittest.mock import patch

    # Mock _handle_push_to_remote to simulate push failure
    with patch("rhiza_tools.commands.bump._handle_push_to_remote", side_effect=typer.Exit(code=1)):
        with pytest.raises(typer.Exit) as excinfo:
            bump_command(version="patch", push=True)
        assert excinfo.value.exit_code == 1


def test_show_file_changes_with_nonexistent_file(bump_project):
    """Test _show_file_changes with nonexistent file."""
    from pathlib import Path

    from rhiza_tools.commands.bump import _show_file_changes

    # This should log a warning but not raise an exception
    _show_file_changes(Path("nonexistent.txt"), "0.1.0", "0.1.1")
    # Test passes if no exception is raised


def test_show_file_changes_with_exception(bump_project, monkeypatch):
    """Test _show_file_changes handles read exceptions."""
    from pathlib import Path
    from unittest.mock import Mock

    from rhiza_tools.commands.bump import _show_file_changes

    # Create a mock Path object that raises an exception on read_text
    mock_path = Mock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.read_text.side_effect = PermissionError("Access denied")

    # This should handle the exception gracefully
    _show_file_changes(mock_path, "0.1.0", "0.1.1")
    # Test passes if no exception is raised


def test_preview_file_modifications_fallback(bump_project):
    """Test _preview_file_modifications uses fallback when config has no files."""
    from unittest.mock import Mock

    from rhiza_tools.commands.bump import _preview_file_modifications

    # Create a mock config with no files_to_modify attribute
    mock_config = Mock()
    mock_config.files_to_modify = []

    # This should fall back to checking common files
    _preview_file_modifications(mock_config, "0.1.0", "0.1.1")
    # Test passes if no exception is raised


def test_log_bump_success_fallback(bump_project):
    """Test _log_bump_success uses fallback when config has no files."""
    from unittest.mock import Mock

    from rhiza_tools.commands.bump import _log_bump_success

    # Bump to a version first
    bump_command(version="patch")

    # Create a mock config with no files_to_modify attribute
    mock_config = Mock()
    mock_config.files_to_modify = []

    # This should fall back to checking common files
    _log_bump_success("0.1.0", mock_config)
    # Test passes if no exception is raised


def test_log_bump_success_with_file_read_exception(bump_project, monkeypatch):
    """Test _log_bump_success handles file read exceptions."""
    from pathlib import Path
    from unittest.mock import Mock

    from rhiza_tools.commands.bump import _log_bump_success

    # Bump to a version first
    bump_command(version="patch")

    # Mock Path.read_text to raise an exception
    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if self.name == "pyproject.toml":
            raise PermissionError("Access denied")  # noqa: TRY003
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    # Create a mock config
    mock_config = Mock()
    mock_config.files_to_modify = []

    # This should handle the exception gracefully
    _log_bump_success("0.1.0", mock_config)
    # Test passes if no exception is raised


def test_branch_checkout_returns_none_when_no_branch(bump_project):
    """Test _handle_branch_checkout returns None when no branch specified."""
    from rhiza_tools.commands.bump import _handle_branch_checkout

    result = _handle_branch_checkout(None, False)
    assert result is None


def test_branch_checkout_returns_none_when_git_fails(bump_project, monkeypatch):
    """Test _handle_branch_checkout returns None when git fails."""
    import subprocess
    from unittest.mock import MagicMock

    from rhiza_tools.commands.bump import _handle_branch_checkout

    # Mock subprocess.run to fail on rev-parse
    original_run = subprocess.run

    def mock_run(cmd, **kwargs):
        if isinstance(cmd, list) and "rev-parse" in cmd:
            result = MagicMock()
            result.returncode = 1
            result.stdout = ""
            result.stderr = "not a git repository"
            return result
        return original_run(cmd, **kwargs)

    monkeypatch.setattr("subprocess.run", mock_run)

    result = _handle_branch_checkout("some-branch", False)
    assert result is None


def test_branch_checkout_returns_none_when_same_branch(bump_project):
    """Test _handle_branch_checkout returns None when already on target branch."""
    import subprocess

    from rhiza_tools.commands.bump import _handle_branch_checkout

    # Get current branch
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
    current_branch = result.stdout.strip()

    # Try to checkout the same branch
    result = _handle_branch_checkout(current_branch, False)
    assert result is None


def test_branch_checkout_fails_gracefully(bump_project, monkeypatch):
    """Test _handle_branch_checkout raises Exit when checkout fails."""
    import subprocess
    from unittest.mock import MagicMock

    from rhiza_tools.commands.bump import _handle_branch_checkout

    # Mock subprocess.run - intercept checkout commands, fall through for rev-parse
    original_run = subprocess.run

    def mock_run(cmd, **kwargs):
        if isinstance(cmd, list) and "checkout" in cmd:
            result = MagicMock()
            result.returncode = 1
            result.stdout = ""
            result.stderr = "error: pathspec 'nonexistent' did not match"
            return result
        return original_run(cmd, **kwargs)

    monkeypatch.setattr("subprocess.run", mock_run)

    # Should raise Exit
    with pytest.raises(typer.Exit) as excinfo:
        _handle_branch_checkout("nonexistent-branch", False)
    assert excinfo.value.exit_code == 1


def test_branch_checkout_dry_run(bump_project):
    """Test _handle_branch_checkout in dry-run mode."""
    import subprocess

    from rhiza_tools.commands.bump import _handle_branch_checkout

    # Get the current default branch name
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
    default_branch = result.stdout.strip()

    # Create a test branch
    subprocess.run(["git", "checkout", "-b", "test-dry-run"], check=True, capture_output=True)
    subprocess.run(["git", "checkout", default_branch], check=True, capture_output=True)

    # In dry-run mode, should not actually checkout
    result_branch = _handle_branch_checkout("test-dry-run", dry_run=True)

    # Should return the original branch name
    assert result_branch == default_branch

    # Verify we're still on default branch
    current = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
    assert current.stdout.strip() == default_branch


def test_restore_original_branch(bump_project):
    """Test _restore_original_branch restores the branch."""
    import subprocess

    from rhiza_tools.commands.bump import _restore_original_branch

    # Get the current default branch name
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
    default_branch = result.stdout.strip()

    # Create and switch to a test branch
    subprocess.run(["git", "checkout", "-b", "test-restore"], check=True, capture_output=True)

    # Restore to default branch
    _restore_original_branch(default_branch, False)

    # Verify we're back on default branch
    current = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
    assert current.stdout.strip() == default_branch


def test_restore_original_branch_dry_run(bump_project):
    """Test _restore_original_branch in dry-run mode."""
    import subprocess

    from rhiza_tools.commands.bump import _restore_original_branch

    # Create and switch to a test branch
    subprocess.run(["git", "checkout", "-b", "test-restore-dry"], check=True, capture_output=True)

    # In dry-run mode, should not restore
    _restore_original_branch("master", dry_run=True)

    # Verify we're still on test branch
    current = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
    assert current.stdout.strip() == "test-restore-dry"


def test_restore_original_branch_none(bump_project):
    """Test _restore_original_branch does nothing when original_branch is None."""
    import subprocess

    from rhiza_tools.commands.bump import _restore_original_branch

    # Get current branch
    before = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)

    # Should do nothing
    _restore_original_branch(None, False)

    # Verify branch unchanged
    after = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
    assert before.stdout == after.stdout
