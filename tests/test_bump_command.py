"""Tests for the bump command."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import tomlkit
import typer
from bumpversion.exceptions import BumpVersionError

from rhiza_tools.commands.bump import (
    BumpOptions,
    Language,
    bump_command,
    get_current_version,
)


@pytest.fixture
def bump_project(temp_project):
    """Create a project with bumpversion config.

    Yields the project path, then asserts no git tags were created.
    """
    rhiza_dir = temp_project / ".rhiza"
    rhiza_dir.mkdir(exist_ok=True)

    config_content = """
[tool.bumpversion]
parse = "(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)(?:[-]?(?P<release>[a-z]+)[\\\\.]?(?P<pre_n>\\\\d+))?(?:\\\\+build\\\\.(?P<build_n>\\\\d+))?"
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
    "a",
    "beta",
    "b",
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
    import shutil
    import subprocess  # nosec B404

    git = shutil.which("git") or "git"
    subprocess.run([git, "add", ".rhiza/.cfg.toml"], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run([git, "commit", "-m", "Add bumpversion config"], check=True, capture_output=True)  # nosec B603 B607

    yield temp_project

    # Safety check: ensure no git tags were created during the test
    result = subprocess.run([git, "tag", "-l"], capture_output=True, text=True, check=False)  # nosec B603 B607
    tags = result.stdout.strip()
    assert tags == "", f"Git tags were unexpectedly created during test: {tags}"


def test_bump_patch(bump_project):
    """Test bumping the patch version."""
    bump_command(BumpOptions(version="patch"))
    assert get_current_version(Language.PYTHON) == "0.1.1"


def test_bump_minor(bump_project):
    """Test bumping the minor version."""
    bump_command(BumpOptions(version="minor"))
    assert get_current_version(Language.PYTHON) == "0.2.0"


def test_bump_major(bump_project):
    """Test bumping the major version."""
    bump_command(BumpOptions(version="major"))
    assert get_current_version(Language.PYTHON) == "1.0.0"


def test_bump_explicit_version(bump_project):
    """Test bumping to an explicit version."""
    bump_command(BumpOptions(version="1.2.3"))
    assert get_current_version(Language.PYTHON) == "1.2.3"


def test_bump_explicit_version_with_v_prefix(bump_project):
    """Test bumping to an explicit version with 'v' prefix."""
    bump_command(BumpOptions(version="v1.2.3"))
    assert get_current_version(Language.PYTHON) == "1.2.3"


def test_dry_run(bump_project):
    """Test dry run does not change the version."""
    bump_command(BumpOptions(version="patch", dry_run=True))
    assert get_current_version(Language.PYTHON) == "0.1.0"


def test_invalid_version(bump_project):
    """Test that invalid versions raise an error."""
    with pytest.raises(typer.Exit):
        bump_command(BumpOptions(version="invalid"))


def test_missing_pyproject_toml(bump_project):
    """Test that missing pyproject.toml raises an error."""
    os.remove("pyproject.toml")
    with pytest.raises(typer.Exit):
        bump_command(BumpOptions(version="patch"))


def test_bump_prerelease(bump_project):
    """Test bumping prerelease."""
    # First bump to a prerelease version
    bump_command(BumpOptions(version="0.1.0-alpha.1"))
    assert get_current_version(Language.PYTHON) == "0.1.0-alpha.1"

    # Bump prerelease
    bump_command(BumpOptions(version="prerelease"))
    assert get_current_version(Language.PYTHON) == "0.1.0-alpha.2"


def test_bump_build(bump_project):
    """Test bumping build."""
    # First bump to a build version
    bump_command(BumpOptions(version="0.1.0+build.1"))
    assert get_current_version(Language.PYTHON) == "0.1.0+build.1"

    # Bump build
    bump_command(BumpOptions(version="build"))
    assert get_current_version(Language.PYTHON) == "0.1.0+build.2"


def test_bump_interactive_patch(bump_project, monkeypatch):
    """Test interactive bump selection (Patch)."""

    # Mock the return value of qs.select(...).ask()
    class MockQuestion:
        def ask(self):
            return "Patch (0.1.0 -> 0.1.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
    monkeypatch.setattr("rhiza_tools.commands.bump._handle_push_to_remote", lambda *a, **kw: None)

    bump_command(BumpOptions(version=None))
    assert get_current_version(Language.PYTHON) == "0.1.1"


def test_bump_interactive_minor(bump_project, monkeypatch):
    """Test interactive bump selection (Minor)."""

    class MockQuestion:
        def ask(self):
            return "Minor (0.1.0 -> 0.2.0)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
    monkeypatch.setattr("rhiza_tools.commands.bump._handle_push_to_remote", lambda *a, **kw: None)

    bump_command(BumpOptions(version=None))
    assert get_current_version(Language.PYTHON) == "0.2.0"


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
        bump_command(BumpOptions(version=None))

    assert excinfo.value.exit_code == 0
    assert get_current_version(Language.PYTHON) == "0.1.0"


def test_bump_alpha_argument(bump_project):
    """Test bumping alpha version via argument."""
    bump_command(BumpOptions(version="alpha"))
    assert get_current_version(Language.PYTHON) == "0.1.1-alpha.1"

    bump_command(BumpOptions(version="alpha"))
    assert get_current_version(Language.PYTHON) == "0.1.1-alpha.2"


def test_bump_beta_argument(bump_project):
    """Test bumping beta version via argument."""
    bump_command(BumpOptions(version="beta"))
    assert get_current_version(Language.PYTHON) == "0.1.1-beta.1"


def test_bump_dev_argument(bump_project):
    """Test bumping dev version via argument."""
    bump_command(BumpOptions(version="dev"))
    assert get_current_version(Language.PYTHON) == "0.1.1-dev.1"


def test_bump_rc_argument(bump_project):
    """Test bumping rc version via argument."""
    bump_command(BumpOptions(version="rc"))
    assert get_current_version(Language.PYTHON) == "0.1.1-rc.1"


def test_bump_prerelease_transition(bump_project):
    """Test transitioning between prerelease types."""
    # Start with alpha
    bump_command(BumpOptions(version="alpha"))
    assert get_current_version(Language.PYTHON) == "0.1.1-alpha.1"

    # Switch to beta
    bump_command(BumpOptions(version="beta"))
    assert get_current_version(Language.PYTHON) == "0.1.1-beta.1"

    # Switch back to alpha (should bump patch and start new alpha)
    # 0.1.1-beta.1 -> alpha -> 0.1.1-alpha.1
    bump_command(BumpOptions(version="alpha"))
    assert get_current_version(Language.PYTHON) == "0.1.1-alpha.1"


def test_bump_interactive_rc(bump_project, monkeypatch):
    """Test interactive bump selection (RC)."""

    class MockQuestion:
        def ask(self):
            return "RC (0.1.0 -> 0.1.1-rc.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
    monkeypatch.setattr("rhiza_tools.commands.bump._handle_push_to_remote", lambda *a, **kw: None)

    bump_command(BumpOptions(version=None))
    assert get_current_version(Language.PYTHON) == "0.1.1-rc.1"


def test_bump_interactive_build(bump_project, monkeypatch):
    """Test interactive bump selection (Build)."""

    class MockQuestion:
        def ask(self):
            return "Build (0.1.0 -> 0.1.0+build.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
    monkeypatch.setattr("rhiza_tools.commands.bump._handle_push_to_remote", lambda *a, **kw: None)

    bump_command(BumpOptions(version=None))
    assert get_current_version(Language.PYTHON) == "0.1.0+build.1"


def test_get_current_version_error_handling(bump_project, monkeypatch):
    """Test error handling when reading version from pyproject.toml fails."""

    def mock_open_error(*args, **kwargs):
        raise OSError("File read error")  # noqa: TRY003

    monkeypatch.setattr("builtins.open", mock_open_error)

    with pytest.raises(typer.Exit) as excinfo:
        get_current_version(Language.PYTHON)
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
        bump_command(BumpOptions(version="patch"))
    assert excinfo.value.exit_code == 1


def test_bump_interactive_alpha(bump_project, monkeypatch):
    """Test interactive bump selection (Alpha)."""

    class MockQuestion:
        def ask(self):
            return "Alpha (0.1.0 -> 0.1.1-alpha.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
    monkeypatch.setattr("rhiza_tools.commands.bump._handle_push_to_remote", lambda *a, **kw: None)

    bump_command(BumpOptions(version=None))
    assert get_current_version(Language.PYTHON) == "0.1.1-alpha.1"


def test_bump_interactive_beta(bump_project, monkeypatch):
    """Test interactive bump selection (Beta)."""

    class MockQuestion:
        def ask(self):
            return "Beta (0.1.0 -> 0.1.1-beta.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
    monkeypatch.setattr("rhiza_tools.commands.bump._handle_push_to_remote", lambda *a, **kw: None)

    bump_command(BumpOptions(version=None))
    assert get_current_version(Language.PYTHON) == "0.1.1-beta.1"


def test_bump_interactive_dev(bump_project, monkeypatch):
    """Test interactive bump selection (Dev)."""

    class MockQuestion:
        def ask(self):
            return "Dev (0.1.0 -> 0.1.1-dev.1)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
    monkeypatch.setattr("rhiza_tools.commands.bump._handle_push_to_remote", lambda *a, **kw: None)

    bump_command(BumpOptions(version=None))
    assert get_current_version(Language.PYTHON) == "0.1.1-dev.1"


def test_bump_interactive_prerelease(bump_project, monkeypatch):
    """Test interactive bump selection (Prerelease)."""
    # First set up a prerelease version
    bump_command(BumpOptions(version="0.1.0-alpha.1"))

    class MockQuestion:
        def ask(self):
            return "Prerelease (0.1.0-alpha.1 -> 0.1.0-alpha.2)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
    monkeypatch.setattr("rhiza_tools.commands.bump._handle_push_to_remote", lambda *a, **kw: None)

    bump_command(BumpOptions(version=None))
    assert get_current_version(Language.PYTHON) == "0.1.0-alpha.2"


def test_bump_interactive_major(bump_project, monkeypatch):
    """Test interactive bump selection (Major)."""

    class MockQuestion:
        def ask(self):
            return "Major (0.1.0 -> 1.0.0)"

    def mock_select(*args, **kwargs):
        return MockQuestion()

    monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
    monkeypatch.setattr("rhiza_tools.commands.bump._handle_push_to_remote", lambda *a, **kw: None)

    bump_command(BumpOptions(version=None))
    assert get_current_version(Language.PYTHON) == "1.0.0"


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
        bump_command(BumpOptions(version=None))
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

    monkeypatch.setattr("rhiza_tools.commands.bump_engine.get_configuration", mock_get_config)

    # Test with allow_dirty=True
    bump_command(BumpOptions(version="patch", allow_dirty=True))
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

    monkeypatch.setattr("rhiza_tools.commands.bump_engine.get_configuration", mock_get_config)

    # Test with commit=True
    bump_command(BumpOptions(version="patch", commit=True))
    assert called_with_params.get("commit") is True


def test_build_changelog_hooks_returns_empty_without_cliff_config(bump_project):
    """No changelog hooks are produced when the project has no git-cliff config."""
    from rhiza_tools.commands.bump import _build_changelog_hooks

    assert _build_changelog_hooks("1.2.3") == []


def test_build_changelog_hooks_present_with_cliff_config(bump_project):
    """A cliff.toml turns on git-cliff hooks that fold CHANGELOG.md into the bump commit."""
    from pathlib import Path

    from rhiza_tools.commands.bump import _build_changelog_hooks

    Path("cliff.toml").write_text("[changelog]\n")
    assert _build_changelog_hooks("1.2.3") == [
        "uvx git-cliff --tag v1.2.3 --output CHANGELOG.md",
        "git add CHANGELOG.md",
    ]


def test_bump_folds_changelog_hook_into_commit(bump_project, monkeypatch):
    """Committing with a cliff.toml present appends the git-cliff hook to the bump commit."""
    from pathlib import Path

    Path("cliff.toml").write_text("[changelog]\n")

    captured = {}

    def mock_do_bump(*args, **kwargs):
        # Capture the config used for the real (non-dry-run) bump commit.
        if kwargs.get("dry_run") is False:
            captured["config"] = kwargs.get("config")

    monkeypatch.setattr("rhiza_tools.commands.bump_engine.do_bump", mock_do_bump)

    bump_command(BumpOptions(version="patch", commit=True))

    hooks = list(captured["config"].pre_commit_hooks)
    assert "uvx git-cliff --tag v0.1.1 --output CHANGELOG.md" in hooks
    assert "git add CHANGELOG.md" in hooks


def test_bump_without_cliff_config_adds_no_changelog_hook(bump_project, monkeypatch):
    """Without a cliff.toml, committing injects no git-cliff hook."""
    captured = {}

    def mock_do_bump(*args, **kwargs):
        if kwargs.get("dry_run") is False:
            captured["config"] = kwargs.get("config")

    monkeypatch.setattr("rhiza_tools.commands.bump_engine.do_bump", mock_do_bump)

    bump_command(BumpOptions(version="patch", commit=True))

    hooks = list(captured["config"].pre_commit_hooks)
    assert not any("git-cliff" in hook for hook in hooks)


def test_bump_configuration_load_failure(bump_project, monkeypatch):
    """Test bump command when configuration loading fails."""

    def mock_get_config(*args, **kwargs):
        from bumpversion.exceptions import ConfigurationError

        raise ConfigurationError("Configuration load error")  # noqa: TRY003

    monkeypatch.setattr("rhiza_tools.commands.bump_engine.get_configuration", mock_get_config)

    # Should fail with exit code 1
    with pytest.raises(typer.Exit) as excinfo:
        bump_command(BumpOptions(version="patch"))
    assert excinfo.value.exit_code == 1


def test_bump_operation_failure(bump_project, monkeypatch):
    """Test bump command when the bump operation fails."""

    def mock_do_bump(*args, **kwargs):
        raise BumpVersionError("Bump operation failed")  # noqa: TRY003

    monkeypatch.setattr("rhiza_tools.commands.bump_engine.do_bump", mock_do_bump)

    # Should fail with exit code 1
    with pytest.raises(typer.Exit) as excinfo:
        bump_command(BumpOptions(version="patch"))
    assert excinfo.value.exit_code == 1


def test_bump_with_push_flag(bump_project):
    """Test bump command with push flag."""
    from unittest.mock import MagicMock, patch

    # Mock _handle_push_to_remote to avoid real git push
    mock_push = MagicMock()
    with patch("rhiza_tools.commands.bump._handle_push_to_remote", mock_push):
        bump_command(BumpOptions(version="patch", push=True))

    assert get_current_version(Language.PYTHON) == "0.1.1"
    mock_push.assert_called_once()


def test_bump_with_branch_flag(bump_project):
    """Test bump command with branch flag."""
    from unittest.mock import MagicMock, patch

    # Mock branch checkout/restore to avoid real git branch operations
    mock_checkout = MagicMock(return_value="original-branch")
    mock_restore = MagicMock()

    with (
        patch("rhiza_tools.commands.bump._handle_branch_checkout", mock_checkout),
        patch("rhiza_tools.commands.bump._restore_original_branch", mock_restore),
    ):
        bump_command(BumpOptions(version="patch", branch="test-branch"))

    assert get_current_version(Language.PYTHON) == "0.1.1"
    mock_checkout.assert_called_once_with("test-branch", False)
    mock_restore.assert_called_once_with("original-branch", False)


def test_bump_push_flag_implies_commit(bump_project):
    """Test that push flag implies commit flag."""
    from unittest.mock import MagicMock, patch

    # Mock _handle_push_to_remote to avoid real git push
    mock_push = MagicMock()
    with patch("rhiza_tools.commands.bump._handle_push_to_remote", mock_push):
        # Call with push=True but commit=False - push should still happen (implies commit)
        bump_command(BumpOptions(version="patch", push=True, commit=False))

    assert get_current_version(Language.PYTHON) == "0.1.1"
    mock_push.assert_called_once()


def test_bump_with_push_failure(bump_project):
    """Test bump command when git push fails."""
    from unittest.mock import patch

    # Mock _handle_push_to_remote to simulate push failure
    with patch("rhiza_tools.commands.bump._handle_push_to_remote", side_effect=typer.Exit(code=1)):
        with pytest.raises(typer.Exit) as excinfo:
            bump_command(BumpOptions(version="patch", push=True))
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
    bump_command(BumpOptions(version="patch"))

    # Create a mock config with no files_to_modify attribute
    mock_config = Mock()
    mock_config.files_to_modify = []

    # This should fall back to checking common files
    _log_bump_success("0.1.0", mock_config, Language.PYTHON)
    # Test passes if no exception is raised


def test_log_bump_success_with_file_read_exception(bump_project, monkeypatch):
    """Test _log_bump_success handles file read exceptions."""
    from pathlib import Path
    from unittest.mock import Mock

    from rhiza_tools.commands.bump import _log_bump_success

    # Bump to a version first
    bump_command(BumpOptions(version="patch"))

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
    _log_bump_success("0.1.0", mock_config, Language.PYTHON)
    # Test passes if no exception is raised


def test_branch_checkout_returns_none_when_no_branch(bump_project):
    """Test _handle_branch_checkout returns None when no branch specified."""
    from rhiza_tools.commands.bump import _handle_branch_checkout

    result = _handle_branch_checkout(None, False)
    assert result is None


def test_branch_checkout_returns_none_when_git_fails(bump_project, monkeypatch):
    """Test _handle_branch_checkout returns None when git fails."""
    import subprocess  # nosec B404
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
    import subprocess  # nosec B404

    from rhiza_tools.commands.bump import _handle_branch_checkout

    # Get current branch
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)  # nosec B603 B607
    current_branch = result.stdout.strip()

    # Try to checkout the same branch
    result = _handle_branch_checkout(current_branch, False)
    assert result is None


def test_branch_checkout_fails_gracefully(bump_project, monkeypatch):
    """Test _handle_branch_checkout raises Exit when checkout fails."""
    import subprocess  # nosec B404
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
    import subprocess  # nosec B404

    from rhiza_tools.commands.bump import _handle_branch_checkout

    # Get the current default branch name
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)  # nosec B603 B607
    default_branch = result.stdout.strip()

    # Create a test branch
    subprocess.run(["git", "checkout", "-b", "test-dry-run"], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run(["git", "checkout", default_branch], check=True, capture_output=True)  # nosec B603 B607

    # In dry-run mode, should not actually checkout
    result_branch = _handle_branch_checkout("test-dry-run", dry_run=True)

    # Should return the original branch name
    assert result_branch == default_branch

    # Verify we're still on default branch
    current = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)  # nosec B603 B607
    assert current.stdout.strip() == default_branch


def test_restore_original_branch(bump_project):
    """Test _restore_original_branch restores the branch."""
    import subprocess  # nosec B404

    from rhiza_tools.commands.bump import _restore_original_branch

    # Get the current default branch name
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)  # nosec B603 B607
    default_branch = result.stdout.strip()

    # Create and switch to a test branch
    subprocess.run(["git", "checkout", "-b", "test-restore"], check=True, capture_output=True)  # nosec B603 B607

    # Restore to default branch
    _restore_original_branch(default_branch, False)

    # Verify we're back on default branch
    current = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)  # nosec B603 B607
    assert current.stdout.strip() == default_branch


def test_restore_original_branch_dry_run(bump_project):
    """Test _restore_original_branch in dry-run mode."""
    import subprocess  # nosec B404

    from rhiza_tools.commands.bump import _restore_original_branch

    # Create and switch to a test branch
    subprocess.run(["git", "checkout", "-b", "test-restore-dry"], check=True, capture_output=True)  # nosec B603 B607

    # In dry-run mode, should not restore
    _restore_original_branch("master", dry_run=True)

    # Verify we're still on test branch
    current = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)  # nosec B603 B607
    assert current.stdout.strip() == "test-restore-dry"


def test_restore_original_branch_none(bump_project):
    """Test _restore_original_branch does nothing when original_branch is None."""
    import subprocess  # nosec B404

    from rhiza_tools.commands.bump import _restore_original_branch

    # Get current branch
    before = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)  # nosec B603 B607

    # Should do nothing
    _restore_original_branch(None, False)

    # Verify branch unchanged
    after = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)  # nosec B603 B607
    assert before.stdout == after.stdout


# ──────────────────────────────────────────────
# Preflight Validation Tests
# ──────────────────────────────────────────────


class TestPreflightValidation:
    """Tests for the preflight dry-run validation in bump_command."""

    def test_preflight_catches_error_before_file_changes(self, bump_project):
        """Preflight failure should leave all files unchanged."""
        from unittest.mock import patch

        original_content = (bump_project / "pyproject.toml").read_text()

        def mock_do_bump(*args, **kwargs):
            from bumpversion.exceptions import BumpVersionError

            # Fail on the preflight (dry_run=True) call
            if kwargs.get("dry_run", False):
                raise BumpVersionError("Simulated preflight failure")  # noqa: TRY003
            # Should never reach the real call
            raise AssertionError("Real bump should not be called after preflight failure")  # noqa: TRY003

        with patch("rhiza_tools.commands.bump_engine.do_bump", side_effect=mock_do_bump):
            with pytest.raises(typer.Exit) as excinfo:
                bump_command(BumpOptions(version="patch"))
            assert excinfo.value.exit_code == 1

        # Verify no file changes were made
        assert (bump_project / "pyproject.toml").read_text() == original_content
        assert get_current_version(Language.PYTHON) == "0.1.0"

    def test_preflight_runs_before_actual_bump(self, bump_project):
        """Preflight dry-run runs before the actual bump for non-dry-run calls."""
        from unittest.mock import patch

        do_bump_calls = []

        def tracking_do_bump(*args, **kwargs):
            do_bump_calls.append({"dry_run": kwargs.get("dry_run", False)})
            # Call through to the real do_bump
            from bumpversion.bump import do_bump as real_do_bump

            return real_do_bump(*args, **kwargs)

        with patch("rhiza_tools.commands.bump_engine.do_bump", side_effect=tracking_do_bump):
            bump_command(BumpOptions(version="patch"))

        # Should have two calls: first dry-run (preflight), then real
        assert len(do_bump_calls) == 2
        assert do_bump_calls[0]["dry_run"] is True  # preflight
        assert do_bump_calls[1]["dry_run"] is False  # actual bump
        assert get_current_version(Language.PYTHON) == "0.1.1"

    def test_preflight_skipped_for_dry_run(self, bump_project):
        """When dry_run=True, preflight is skipped (only actual dry-run runs)."""
        from unittest.mock import patch

        do_bump_calls = []

        def tracking_do_bump(*args, **kwargs):
            do_bump_calls.append({"dry_run": kwargs.get("dry_run", False)})
            from bumpversion.bump import do_bump as real_do_bump

            return real_do_bump(*args, **kwargs)

        with patch("rhiza_tools.commands.bump_engine.do_bump", side_effect=tracking_do_bump):
            bump_command(BumpOptions(version="patch", dry_run=True))

        # Should have only one call (the actual dry-run), no preflight
        assert len(do_bump_calls) == 1
        assert do_bump_calls[0]["dry_run"] is True
        assert get_current_version(Language.PYTHON) == "0.1.0"  # unchanged


# Tests for Go project support


@pytest.fixture
def go_project(tmp_path, monkeypatch):
    """Create a temporary Go project directory with git and VERSION file.

    This fixture:
    - Creates a temporary directory
    - Initializes a git repository
    - Creates a go.mod file
    - Creates a VERSION file with version 0.1.0
    - Creates bumpversion configuration for VERSION file
    - Changes working directory to the temp project
    - Returns the path to the temporary project
    """
    import subprocess  # nosec B404

    # Change to temporary directory
    monkeypatch.chdir(tmp_path)

    # Prevent git from walking up to the real repo if anything goes wrong
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    # Initialize git repository
    import shutil

    git = shutil.which("git") or "git"
    subprocess.run([git, "init"], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run([git, "config", "user.email", "test@example.com"], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run([git, "config", "user.name", "Test User"], check=True, capture_output=True)  # nosec B603 B607

    # Create go.mod
    gomod_content = """module github.com/example/test-go-project

go 1.23
"""
    gomod_path = tmp_path / "go.mod"
    gomod_path.write_text(gomod_content)

    # Create VERSION file with initial version
    version_path = tmp_path / "VERSION"
    version_path.write_text("0.1.0\n")

    # Create .rhiza directory and config
    rhiza_dir = tmp_path / ".rhiza"
    rhiza_dir.mkdir(exist_ok=True)

    # Note: Quadruple backslashes are correct here:
    # Python string -> TOML file (\\\\d becomes \\d) -> regex pattern (\d)
    config_content = """
[tool.bumpversion]
parse = "(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)(?:[-]?(?P<release>[a-z]+)[\\\\.]?(?P<pre_n>\\\\d+))?(?:\\\\+build\\\\.(?P<build_n>\\\\d+))?"
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
    "a",
    "beta",
    "b",
    "rc",
    "prod"
]

[[tool.bumpversion.files]]
filename = "VERSION"
"""  # noqa: E501
    with open(rhiza_dir / ".cfg.toml", "w") as f:
        f.write(config_content)

    # Commit the initial state
    subprocess.run([git, "add", "."], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run([git, "commit", "-m", "Initial commit"], check=True, capture_output=True)  # nosec B603 B607

    yield tmp_path

    # Safety check: ensure no git tags were created during the test
    result = subprocess.run([git, "tag", "-l"], capture_output=True, text=True, check=False)  # nosec B603 B607
    tags = result.stdout.strip()
    assert tags == "", f"Git tags were unexpectedly created during test: {tags}"


def test_go_project_bump_patch(go_project):
    """Test bumping the patch version in a Go project."""
    bump_command(BumpOptions(version="patch", language=Language.GO))
    assert get_current_version(Language.GO) == "0.1.1"


def test_go_project_bump_minor(go_project):
    """Test bumping the minor version in a Go project."""
    bump_command(BumpOptions(version="minor", language=Language.GO))
    assert get_current_version(Language.GO) == "0.2.0"


def test_go_project_bump_major(go_project):
    """Test bumping the major version in a Go project."""
    bump_command(BumpOptions(version="major", language=Language.GO))
    assert get_current_version(Language.GO) == "1.0.0"


def test_go_project_bump_explicit_version(go_project):
    """Test bumping to an explicit version in a Go project."""
    bump_command(BumpOptions(version="2.3.4", language=Language.GO))
    assert get_current_version(Language.GO) == "2.3.4"


def test_version_file_only_project(tmp_path, monkeypatch):
    """Test bump with only VERSION file (no pyproject.toml or go.mod)."""
    import subprocess  # nosec B404

    # Change to temporary directory
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    # Initialize git repository
    import shutil

    git = shutil.which("git") or "git"
    subprocess.run([git, "init"], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run([git, "config", "user.email", "test@example.com"], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run([git, "config", "user.name", "Test User"], check=True, capture_output=True)  # nosec B603 B607

    # Create VERSION file
    version_path = tmp_path / "VERSION"
    version_path.write_text("1.0.0\n")

    # Create .rhiza directory and config
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
    with open(rhiza_dir / ".cfg.toml", "w") as f:
        f.write(config_content)

    # Commit the initial state
    subprocess.run([git, "add", "."], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run([git, "commit", "-m", "Initial commit"], check=True, capture_output=True)  # nosec B603 B607

    # Test bump - VERSION file only is not supported anymore, need to add go.mod
    # Create go.mod to make it a Go project
    gomod_path = tmp_path / "go.mod"
    gomod_path.write_text("module example.com/test\n\ngo 1.23\n")
    subprocess.run([git, "add", "go.mod"], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run([git, "commit", "-m", "Add go.mod"], check=True, capture_output=True)  # nosec B603 B607

    bump_command(BumpOptions(version="patch", language=Language.GO))
    assert get_current_version(Language.GO) == "1.0.1"


def test_detect_project_language_python(temp_project):
    """Test language detection for Python projects."""
    assert Language.detect() == Language.PYTHON


def test_detect_project_language_go(go_project):
    """Test language detection for Go projects."""
    assert Language.detect() == Language.GO


def test_detect_project_language_none(tmp_path, monkeypatch):
    """Test language detection when no supported files exist."""
    monkeypatch.chdir(tmp_path)
    assert Language.detect() is None


def test_get_interactive_bump_type_with_eoferror(bump_project, monkeypatch):
    """Test get_interactive_bump_type handles EOFError in non-interactive mode."""
    from unittest.mock import MagicMock

    from rhiza_tools.commands.bump import get_interactive_bump_type

    # Mock questionary to raise EOFError (simulating non-interactive environment)
    mock_select = MagicMock()
    mock_select.ask.side_effect = EOFError

    import questionary as qs

    monkeypatch.setattr(qs, "select", lambda *args, **kwargs: mock_select)

    # Should raise typer.Exit with code 1
    with pytest.raises(typer.Exit) as exc_info:
        get_interactive_bump_type("1.0.0")
    assert exc_info.value.exit_code == 1


def test_get_interactive_bump_type_with_invalid_choice(bump_project, monkeypatch):
    """Test get_interactive_bump_type handles invalid choice format."""
    from unittest.mock import MagicMock

    from rhiza_tools.commands.bump import get_interactive_bump_type

    # Mock questionary to return a choice without the expected format
    mock_select = MagicMock()
    mock_select.ask.return_value = "Invalid Choice Format"

    import questionary as qs

    monkeypatch.setattr(qs, "select", lambda *args, **kwargs: mock_select)

    # Should raise typer.Exit with code 1
    with pytest.raises(typer.Exit) as exc_info:
        get_interactive_bump_type("1.0.0")
    assert exc_info.value.exit_code == 1


def test_handle_push_to_remote_non_interactive(bump_project, monkeypatch):
    """Test _handle_push_to_remote does not push in non-interactive environment."""
    from unittest.mock import MagicMock

    from rhiza_tools.commands.bump import _handle_push_to_remote

    # Mock questionary to raise EOFError
    mock_confirm = MagicMock()
    mock_confirm.ask.side_effect = EOFError

    import questionary as qs

    monkeypatch.setattr(qs, "confirm", lambda *args, **kwargs: mock_confirm)

    # Mock run_git_command to track if push was attempted
    push_attempted = []

    def mock_run_git(*args, **kwargs):
        push_attempted.append(args)
        return MagicMock(returncode=0, stdout="", stderr="")

    from rhiza_tools.commands import bump

    monkeypatch.setattr(bump, "run_git_command", mock_run_git)

    # Call without version (interactive mode) which should handle EOFError
    _handle_push_to_remote(version=None)

    # Verify push was NOT attempted
    assert len(push_attempted) == 0, "Push should not be attempted in non-interactive environment"


def test_go_project_whitespace_only_version_file(go_project, monkeypatch):
    """Test that VERSION file with only whitespace is rejected."""
    # Write whitespace-only content to VERSION file
    version_file = go_project / "VERSION"
    version_file.write_text("   \n\t  \n   ")

    monkeypatch.chdir(go_project)

    # Should raise typer.Exit with error about empty file
    with pytest.raises(typer.Exit) as exc_info:
        get_current_version(Language.GO)
    assert exc_info.value.exit_code == 1


def test_bump_custom_config_path(temp_project):
    """Test that --config flag uses the specified config file path."""
    import shutil
    import subprocess  # nosec B404

    git = shutil.which("git") or "git"

    # Write the bumpversion config to a non-default location
    custom_config_dir = temp_project / "custom"
    custom_config_dir.mkdir()
    custom_config_path = custom_config_dir / "bumpversion.toml"

    config_content = """
[tool.bumpversion]
parse = "(?P<major>\\\\d+)\\\\.(?P<minor>\\\\d+)\\\\.(?P<patch>\\\\d+)"
serialize = ["{major}.{minor}.{patch}"]
search = "{current_version}"
replace = "{new_version}"
regex = false
ignore_missing_version = false
tag = false
commit = false

[[tool.bumpversion.files]]
filename = "pyproject.toml"
search = 'version = "{current_version}"'
replace = 'version = "{new_version}"'
"""
    custom_config_path.write_text(config_content)

    subprocess.run([git, "add", str(custom_config_path)], check=True, capture_output=True)  # nosec B603 B607
    subprocess.run([git, "commit", "-m", "Add custom bumpversion config"], check=True, capture_output=True)  # nosec B603 B607

    # Bump using the custom config path
    bump_command(BumpOptions(version="patch", config=custom_config_path))
    assert get_current_version(Language.PYTHON) == "0.1.1"

    # Safety check: ensure no git tags were created
    result = subprocess.run([git, "tag", "-l"], capture_output=True, text=True, check=False)  # nosec B603 B607
    assert result.stdout.strip() == "", "No git tags should be created"


def test_bump_missing_custom_config_path(temp_project):
    """Test that a non-existent custom config path raises an error."""
    nonexistent_path = temp_project / "nonexistent" / "config.toml"
    with pytest.raises(typer.Exit):
        bump_command(BumpOptions(version="patch", config=nonexistent_path))


# ---------------------------------------------------------------------------
# Branch/edge-case coverage relocated from the former test_coverage_100.py
# ---------------------------------------------------------------------------


class TestDenormalizePep440:
    """bump.py:70-81 – PEP 440 prerelease match path."""

    def test_alpha_long_form(self):
        """Converts 1.0.0alpha1 -> 1.0.0-alpha.1."""
        from rhiza_tools.commands.bump import _denormalize_pep440_to_semver

        assert _denormalize_pep440_to_semver("1.0.0alpha1") == "1.0.0-alpha.1"

    def test_alpha_short_form(self):
        """Converts 1.0.0a1 -> 1.0.0-alpha.1."""
        from rhiza_tools.commands.bump import _denormalize_pep440_to_semver

        assert _denormalize_pep440_to_semver("1.0.0a1") == "1.0.0-alpha.1"

    def test_beta_short_form(self):
        """Converts 1.0.0b2 -> 1.0.0-beta.2."""
        from rhiza_tools.commands.bump import _denormalize_pep440_to_semver

        assert _denormalize_pep440_to_semver("1.0.0b2") == "1.0.0-beta.2"

    def test_beta_long_form(self):
        """Converts 1.0.0beta2 -> 1.0.0-beta.2."""
        from rhiza_tools.commands.bump import _denormalize_pep440_to_semver

        assert _denormalize_pep440_to_semver("1.0.0beta2") == "1.0.0-beta.2"

    def test_rc_form(self):
        """Converts 1.0.0rc3 -> 1.0.0-rc.3."""
        from rhiza_tools.commands.bump import _denormalize_pep440_to_semver

        assert _denormalize_pep440_to_semver("1.0.0rc3") == "1.0.0-rc.3"

    def test_dev_form(self):
        """Converts 1.0.0dev1 -> 1.0.0-dev.1."""
        from rhiza_tools.commands.bump import _denormalize_pep440_to_semver

        assert _denormalize_pep440_to_semver("1.0.0dev1") == "1.0.0-dev.1"


class TestLanguageGetVersionFile:
    """Tests for Language.get_version_file() for each language variant."""

    def test_python_version_file(self):
        """bump.py:129 – Language.PYTHON returns Path('pyproject.toml')."""
        from rhiza_tools.commands.bump import Language

        assert Language.PYTHON.get_version_file() == Path("pyproject.toml")

    def test_go_version_file(self):
        """bump.py:131 – Language.GO returns Path('VERSION')."""
        from rhiza_tools.commands.bump import Language

        assert Language.GO.get_version_file() == Path("VERSION")


class TestGetCurrentVersionBump:
    """Tests for uncovered branches in bump.py get_current_version."""

    def test_go_version_read_exception(self, tmp_path, monkeypatch):
        """bump.py:207-209 – exits when VERSION file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        from rhiza_tools.commands.bump import Language, get_current_version

        with pytest.raises(typer.Exit):
            get_current_version(Language.GO)

    def test_go_version_empty_file(self, tmp_path, monkeypatch):
        """bump.py:211-213 – exits when VERSION file is empty."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "VERSION").write_text("")
        from rhiza_tools.commands.bump import Language, get_current_version

        with pytest.raises(typer.Exit):
            get_current_version(Language.GO)

    def test_go_version_whitespace_only_defensive_check(self, tmp_path, monkeypatch):
        """bump.py:217-218 – defensive check exits when version is whitespace-only."""
        monkeypatch.chdir(tmp_path)
        from rhiza_tools.commands.bump import Language, get_current_version

        # Build a mock where f.read().strip() returns a truthy value with isspace()=True.
        # This covers the defensive check that can't be reached via normal file I/O
        # (strip() always yields either "" or a non-whitespace-bounded string).
        stripped = MagicMock()
        stripped.isspace.return_value = True

        read_val = MagicMock()
        read_val.strip.return_value = stripped

        file_ctx = MagicMock()
        file_ctx.__enter__ = lambda s: file_ctx
        file_ctx.__exit__ = MagicMock(return_value=False)
        file_ctx.read.return_value = read_val

        with patch("builtins.open", return_value=file_ctx), pytest.raises(typer.Exit):
            get_current_version(Language.GO)

    def test_unsupported_language_exits(self, tmp_path, monkeypatch):
        """bump.py:222-223 – exits for unsupported language value."""
        monkeypatch.chdir(tmp_path)
        from rhiza_tools.commands.bump import get_current_version

        with pytest.raises(typer.Exit):
            get_current_version("ruby")  # type: ignore[arg-type]


class TestValidateProjectExists:
    """Tests for uncovered branches in _validate_project_exists."""

    def test_python_missing_pyproject(self, tmp_path, monkeypatch):
        """bump.py:456-458 – exits when pyproject.toml is missing for Python."""
        monkeypatch.chdir(tmp_path)
        from rhiza_tools.commands.bump import Language, _validate_project_exists

        with pytest.raises(typer.Exit):
            _validate_project_exists(Language.PYTHON)

    def test_go_missing_go_mod(self, tmp_path, monkeypatch):
        """bump.py:461-463 – exits when go.mod is missing for Go."""
        monkeypatch.chdir(tmp_path)
        from rhiza_tools.commands.bump import Language, _validate_project_exists

        with pytest.raises(typer.Exit):
            _validate_project_exists(Language.GO)

    def test_go_has_go_mod_but_missing_version_file(self, tmp_path, monkeypatch):
        """bump.py:465-470 – exits when VERSION file is missing despite go.mod."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "go.mod").write_text("module example.com/mymod\ngo 1.21\n")
        from rhiza_tools.commands.bump import Language, _validate_project_exists

        with pytest.raises(typer.Exit):
            _validate_project_exists(Language.GO)

    def test_unsupported_language_exits(self, tmp_path, monkeypatch):
        """bump.py:468-470 – exits for unknown language in _validate_project_exists."""
        monkeypatch.chdir(tmp_path)
        from rhiza_tools.commands.bump import _validate_project_exists

        with pytest.raises(typer.Exit):
            _validate_project_exists("ruby")  # type: ignore[arg-type]


class TestExecuteBump:
    """Tests for uncovered exception paths in _execute_bump."""

    def test_do_bump_exception_not_dry_run(self):
        """bump.py:636-644 – error messages printed and Exit raised when do_bump fails."""
        from rhiza_tools.commands.bump import _execute_bump

        mock_config = MagicMock()
        mock_config_path = MagicMock()

        with (
            patch("rhiza_tools.commands.bump_engine.do_bump", side_effect=BumpVersionError("bump failed")),
            pytest.raises(typer.Exit),
        ):
            _execute_bump("1.0.1", mock_config, mock_config_path, dry_run=False)

    def test_do_bump_exception_dry_run(self):
        """bump.py:636-637,644 – Exit raised in dry_run mode when do_bump fails."""
        from rhiza_tools.commands.bump import _execute_bump

        mock_config = MagicMock()
        mock_config_path = MagicMock()

        with (
            patch("rhiza_tools.commands.bump_engine.do_bump", side_effect=BumpVersionError("bump failed")),
            pytest.raises(typer.Exit),
        ):
            _execute_bump("1.0.1", mock_config, mock_config_path, dry_run=True)


class TestShowInteractivePreview:
    """Tests for uncovered branches in _show_interactive_preview."""

    def test_user_does_not_proceed(self):
        """bump.py:757 – returns (False, False, False) when user cancels."""
        from rhiza_tools.commands.bump import _show_interactive_preview

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False

        with patch("questionary.confirm", return_value=mock_confirm):
            result = _show_interactive_preview("1.0.0", "1.0.1", "main")

        assert result == (False, False, False)


class TestHandlePushToRemote:
    """Tests for uncovered branches in _handle_push_to_remote."""

    def test_user_cancels_interactive_push(self):
        """bump.py:791-792 – user says No to push prompt returns early."""
        from rhiza_tools.commands.bump import _handle_push_to_remote

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = False

        with patch("questionary.confirm", return_value=mock_confirm):
            _handle_push_to_remote(None)  # version=None triggers interactive prompt

    def test_push_succeeds(self):
        """bump.py:799-802 – successful git push prints success message."""
        from rhiza_tools.commands.bump import _handle_push_to_remote

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("rhiza_tools.commands.bump.run_git_command", return_value=mock_result):
            _handle_push_to_remote("1.0.1")  # version set -> no interactive prompt

    def test_push_fails(self):
        """bump.py:803-809 – git push failure raises Exit."""
        from rhiza_tools.commands.bump import _handle_push_to_remote

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "remote: permission denied"

        with (
            patch("rhiza_tools.commands.bump.run_git_command", return_value=mock_result),
            pytest.raises(typer.Exit),
        ):
            _handle_push_to_remote("1.0.1")


class TestBumpCommandCancelled:
    """Tests for interactive cancellation and dry-run log paths in bump_command."""

    def test_bump_cancelled_by_user(self, temp_project):
        """bump.py:914-915 – bump cancelled in interactive mode raises Exit(0)."""
        from rhiza_tools.commands.bump import BumpOptions, bump_command

        with (
            patch("rhiza_tools.commands.bump.get_interactive_bump_type", return_value="1.0.1"),
            patch("rhiza_tools.commands.bump._show_interactive_preview", return_value=(False, False, False)),
            patch("rhiza_tools.commands.bump._build_configuration") as mock_build,
            patch("rhiza_tools.commands.bump._preview_file_modifications"),
            patch("rhiza_tools.commands.bump.get_current_git_branch", return_value="main"),
        ):
            mock_config = MagicMock()
            mock_build.return_value = (mock_config, Path(".bumpversion.toml"))
            options = BumpOptions(version=None, dry_run=False)
            with pytest.raises(typer.Exit) as exc_info:
                bump_command(options)
            assert exc_info.value.exit_code == 0

    def test_dry_run_with_commit_and_push(self, temp_project):
        """bump.py:930,932 – dry_run logs 'Would commit' and 'Would push'."""
        from rhiza_tools.commands.bump import BumpOptions, bump_command

        with (
            patch("rhiza_tools.commands.bump._build_configuration") as mock_build,
            patch("rhiza_tools.commands.bump._preview_file_modifications"),
            patch("rhiza_tools.commands.bump.get_current_git_branch", return_value="main"),
            patch("rhiza_tools.commands.bump._execute_bump"),
            patch("rhiza_tools.commands.bump._parse_version_argument", return_value="1.0.1"),
        ):
            mock_config = MagicMock()
            mock_build.return_value = (mock_config, Path(".bumpversion.toml"))
            options = BumpOptions(version="1.0.1", dry_run=True, commit=True, push=True)
            bump_command(options)  # Should not raise
