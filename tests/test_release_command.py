"""Tests for release command in rhiza_tools.commands.release."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
import typer

from rhiza_tools.commands.bump import BumpOptions, Language, get_current_version
from rhiza_tools.commands.release import (
    check_branch_status,
    check_clean_working_tree,
    check_tag_exists,
    get_default_branch,
    push_tag,
    release_command,
    run_git_command,
)


@pytest.fixture
def mock_pyproject(tmp_path, monkeypatch):
    """Create a temporary pyproject.toml file."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "test-project"
version = "1.2.3"
"""
    )
    monkeypatch.chdir(tmp_path)
    return pyproject


def test_get_current_version(mock_pyproject):
    """Test reading version from pyproject.toml."""
    version = get_current_version(Language.PYTHON)
    assert version == "1.2.3"


def test_get_current_version_missing_file(tmp_path, monkeypatch):
    """Test error when pyproject.toml is missing."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(typer.Exit):
        get_current_version(Language.PYTHON)


def test_run_git_command_success():
    """Test successful git command execution."""
    result = run_git_command(["git", "--version"])
    assert result.returncode == 0
    assert "git version" in result.stdout


def test_run_git_command_failure():
    """Test failed git command execution."""
    with pytest.raises(subprocess.CalledProcessError):
        run_git_command(["git", "invalid-command"])


def test_run_git_command_no_check():
    """Test git command without check flag."""
    result = run_git_command(["git", "invalid-command"], check=False)
    assert result.returncode != 0


def test_check_clean_working_tree_clean(monkeypatch):
    """Test check_clean_working_tree with clean working tree."""
    mock_result = MagicMock()
    mock_result.stdout = ""
    mock_result.returncode = 0

    with patch("rhiza_tools.commands.release.run_git_command", return_value=mock_result):
        check_clean_working_tree()  # Should not raise


def test_check_clean_working_tree_dirty(monkeypatch):
    """Test check_clean_working_tree with uncommitted changes."""
    mock_result = MagicMock()
    mock_result.stdout = " M file.txt\n"
    mock_result.returncode = 0

    with patch("rhiza_tools.commands.release.run_git_command", return_value=mock_result), pytest.raises(typer.Exit):
        check_clean_working_tree()


def test_check_branch_status_up_to_date(monkeypatch):
    """Test check_branch_status when branch is up-to-date."""
    commit_hash = "abc123"

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        if "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = commit_hash
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        check_branch_status("main")  # Should not raise


def test_check_branch_status_behind(monkeypatch):
    """Test check_branch_status when branch is behind remote."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        if "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "rev-parse" in cmd and "@" in cmd and "origin" not in str(cmd):
            result.stdout = "abc123"  # local
        elif "origin/main" in str(cmd):
            result.stdout = "def456"  # remote (different)
        elif "merge-base" in cmd:
            result.stdout = "abc123"  # base == local (behind)
        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        pytest.raises(typer.Exit),
    ):
        check_branch_status("main")


def test_check_branch_status_ahead(monkeypatch):
    """Test check_branch_status when branch is ahead of remote."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        if "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "rev-parse" in cmd and "@" in cmd and "origin" not in str(cmd):
            result.stdout = "def456"  # local
        elif "origin/main" in str(cmd):
            result.stdout = "abc123"  # remote (different)
        elif "merge-base" in cmd:
            result.stdout = "abc123"  # base == remote (ahead)
        elif "log" in cmd:
            result.stdout = "* abc123 commit message\n"
        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        pytest.raises(typer.Exit),
    ):
        check_branch_status("main")


def test_check_branch_status_diverged(monkeypatch):
    """Test check_branch_status when branches have diverged."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        if "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "rev-parse" in cmd and "@" in cmd and "origin" not in str(cmd):
            result.stdout = "abc123"  # local
        elif "origin/main" in str(cmd):
            result.stdout = "def456"  # remote
        elif "merge-base" in cmd:
            result.stdout = "xyz789"  # base (different from both)
        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        pytest.raises(typer.Exit),
    ):
        check_branch_status("main")


def test_get_default_branch():
    """Test getting default branch from remote."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "* remote origin\n  HEAD branch: main\n  Remote branch: main\n"
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        branch = get_default_branch()
        assert branch == "main"


def test_get_default_branch_failure():
    """Test error when default branch cannot be determined."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        pytest.raises(typer.Exit),
    ):
        get_default_branch()


def test_check_tag_exists():
    """Test checking if tag exists locally and remotely."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        if "rev-parse" in cmd:
            result.returncode = 0  # exists locally
        elif "ls-remote" in cmd:
            result.returncode = 1  # doesn't exist remotely
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        local, remote = check_tag_exists("v1.0.0")
        assert local is True
        assert remote is False


def test_push_tag(monkeypatch):
    """Test pushing a tag to remote."""
    mock_run_git = MagicMock()
    mock_result = MagicMock()
    mock_result.stdout = "https://github.com/user/repo.git"
    mock_run_git.return_value = mock_result

    with patch("rhiza_tools.commands.release.run_git_command", mock_run_git):
        push_tag("v1.0.0", dry_run=False)

        # Should call git push
        calls = [c[0][0] for c in mock_run_git.call_args_list]
        push_calls = [c for c in calls if "push" in c]
        assert len(push_calls) > 0


def test_push_tag_dry_run(monkeypatch):
    """Test pushing a tag in dry-run mode."""
    mock_run_git = MagicMock()
    mock_result = MagicMock()
    mock_result.stdout = "https://github.com/user/repo.git"
    mock_run_git.return_value = mock_result

    with patch("rhiza_tools.commands.release.run_git_command", mock_run_git):
        push_tag("v1.0.0", dry_run=True)

        # Should not push in dry-run
        calls = [c[0][0] for c in mock_run_git.call_args_list]
        push_calls = [c for c in calls if "push" in c]
        assert len(push_calls) == 0


def test_release_command_missing_pyproject(tmp_path, monkeypatch):
    """Test release_command when pyproject.toml is missing."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(typer.Exit):
        release_command()


def test_release_command_dry_run(mock_pyproject, monkeypatch):
    """Test release_command in dry-run mode."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.stdout = "abc123"  # Tag exists locally
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1  # Tag doesn't exist remotely
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.2\nv1.2.1"  # Previous tags
        elif "rev-list" in cmd:
            result.stdout = "5"  # 5 commits
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        patch("rhiza_tools.commands.release.typer.confirm", return_value=True),
    ):
        release_command(dry_run=True)  # Should complete without errors


def test_release_command_tag_missing(mock_pyproject, monkeypatch):
    """Test release_command when tag doesn't exist locally."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.returncode = 1  # Tag doesn't exist locally
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd and "--tags" in cmd:
            result.returncode = 1  # Tag doesn't exist remotely

        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        pytest.raises(typer.Exit),
    ):
        release_command()


def test_release_command_tag_exists_remotely(mock_pyproject, monkeypatch):
    """Test release_command when tag already exists on remote."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd and "--tags" in cmd:
            result.returncode = 0  # Tag exists remotely

        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        pytest.raises(typer.Exit),
    ):
        release_command()


def test_check_branch_status_no_upstream(monkeypatch):
    """Test error when no upstream branch is configured."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        if "--symbolic-full-name" in cmd:
            result.returncode = 1  # No upstream
        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        pytest.raises(typer.Exit),
    ):
        check_branch_status("main")


def test_check_branch_status_ahead_of_remote(monkeypatch):
    """Test warning when branch is ahead of remote."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "--symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "rev-parse" in cmd and "@" in cmd:
            result.stdout = "def456"  # local commit
        elif "rev-parse" in cmd:
            result.stdout = "abc123"  # remote commit
        elif "merge-base" in cmd:
            result.stdout = "abc123"  # base is same as remote
        elif "log" in cmd:
            result.stdout = "* def456 Local commit\n"

        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        pytest.raises(typer.Exit),
    ):
        check_branch_status("main")


def test_get_default_branch_no_head_branch(monkeypatch):
    """Test error when default branch cannot be found in remote output."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "* remote origin\n  some other info\n"  # No HEAD branch line
        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        pytest.raises(typer.Exit),
    ):
        get_default_branch()


def test_push_tag_ssh_url(monkeypatch):
    """Test pushing tag with SSH GitHub URL."""
    mock_run_git = MagicMock()
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "git@github.com:user/repo.git"
    mock_run_git.return_value = mock_result

    with patch("rhiza_tools.commands.release.run_git_command", mock_run_git):
        push_tag("v1.0.0", dry_run=False, non_interactive=True)

        # Should push the tag
        calls = [c[0][0] for c in mock_run_git.call_args_list]
        push_calls = [c for c in calls if "push" in c]
        assert len(push_calls) == 1


def test_release_command_non_default_branch_non_interactive(mock_pyproject, monkeypatch):
    """Test release from non-default branch in non-interactive mode."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "feature-branch"  # Not on main
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/feature-branch"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.stdout = "abc123"  # Tag exists locally
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1  # Tag doesn't exist remotely
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.2\nv1.2.1"
        elif "rev-list" in cmd:
            result.stdout = "5"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        # Should not raise in non-interactive mode
        release_command(dry_run=True, non_interactive=True)


def test_release_command_with_commit_count(mock_pyproject, monkeypatch):
    """Test release showing commit count since last tag."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.3\nv1.2.2\nv1.2.1"  # Include current tag in list
        elif "rev-list" in cmd:
            result.stdout = "10"  # 10 commits since last tag
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        release_command(dry_run=True, non_interactive=True)


def test_release_command_user_declines_push(mock_pyproject, monkeypatch):
    """Test release when user declines to push tag."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.2\nv1.2.1"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        patch("typer.confirm", return_value=False),
        pytest.raises(typer.Exit) as exc_info,
    ):
        release_command(dry_run=False, non_interactive=False)
    assert exc_info.value.exit_code == 0


def test_release_command_success_non_dry_run(mock_pyproject, monkeypatch):
    """Test successful release in non-dry-run mode."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.2\nv1.2.1"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"
        elif "push" in cmd:
            result.returncode = 0

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        # Should complete successfully in non-interactive mode
        release_command(dry_run=False, non_interactive=True)


def test_release_command_user_declines_non_default_branch(mock_pyproject, monkeypatch):
    """Test release when user declines to proceed from non-default branch."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "feature-branch"  # Not on default branch
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/feature-branch"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1

        return result

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        patch("typer.confirm", return_value=False),
        pytest.raises(typer.Exit) as exc_info,
    ):
        release_command(dry_run=False, non_interactive=False)
    assert exc_info.value.exit_code == 0


def test_release_with_bump_flag(mock_pyproject, monkeypatch):
    """Test release command with bump flag."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.4" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.3\nv1.2.2"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    # Mock bump_command
    bump_called = {"called": False, "options": None}

    def mock_bump_command(options):
        bump_called["called"] = True
        bump_called["options"] = options
        # Update pyproject.toml version
        import tomlkit

        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())
        data["project"]["version"] = "1.2.4"
        with open("pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(data))

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command),
    ):
        release_command(bump_type="PATCH", push=True, dry_run=True)

    assert bump_called["called"]
    assert isinstance(bump_called["options"], BumpOptions)
    assert bump_called["options"].version == "1.2.4"


def test_release_with_push_flag(mock_pyproject, monkeypatch):
    """Test release command with push flag."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.2\nv1.2.1"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"
        elif "push" in cmd:
            result.returncode = 0

        return result

    push_called = {"called": False}

    def mock_push_tag(tag, dry_run=False, non_interactive=False):
        push_called["called"] = True

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        patch("rhiza_tools.commands.release.push_tag", side_effect=mock_push_tag),
    ):
        release_command(push=True)

    assert push_called["called"]


def test_release_non_interactive_with_bump(mock_pyproject, monkeypatch):
    """Test release in non-interactive mode with bump."""
    git_push_calls = []

    def track_push(cmd, result):
        git_push_calls.append(cmd)

    mock_git = _make_mock_git_for_bump_release(
        callbacks={"push_branch": track_push, "push": track_push},
    )

    # Mock bump_command
    bump_called = {"called": False}

    def mock_bump_command(version, **kwargs):
        bump_called["called"] = True
        # Update pyproject.toml version
        import tomlkit

        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())
        data["project"]["version"] = "1.2.4"
        with open("pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(data))

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git),
        patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command),
    ):
        release_command(bump_type="MINOR", push=True, non_interactive=True)

    assert bump_called["called"]
    # Verify the bump commit was pushed to remote
    assert any("push" in cmd and "origin" in cmd and "main" in cmd for cmd in git_push_calls), (
        "Expected bump commit to be pushed to remote with 'git push origin main'"
    )


def _make_mock_git_for_bump_release(
    version="1.2.4",
    tag_exists_remotely=False,
    previous_tags="v1.2.3\nv1.2.2",
    callbacks=None,
):
    """Build a mock for run_git_command suitable for bump+release tests.

    Args:
        version: The version string the tag will reference.
        tag_exists_remotely: Whether the tag exists on the remote.
        previous_tags: Newline-separated list of existing tags.
        callbacks: Optional dict mapping command categories to callables
            that receive (cmd, result) and can mutate result or record calls.
    """
    if callbacks is None:
        callbacks = {}

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        category = _categorize_git_command(cmd, version)
        if category in callbacks:
            callbacks[category](cmd, result)
        elif category == "branch_name":
            result.stdout = "main"
        elif category == "symbolic_ref":
            result.stdout = "origin/main"
        elif category == "remote_show":
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif category == "rev_parse_tag" or category == "rev_parse" or category == "merge_base":
            result.stdout = "abc123"
        elif category == "ls_remote":
            result.returncode = 0 if tag_exists_remotely else 1
        elif category == "tag_sort":
            result.stdout = previous_tags
        elif category == "remote_url":
            result.stdout = "https://github.com/user/repo.git"

        return result

    return mock_run_git_command


def _categorize_rev_parse_command(cmd, version=""):
    """Categorize a rev-parse git command into a simple string label."""
    if "--abbrev-ref" in cmd:
        return "symbolic_ref" if "--symbolic-full-name" in cmd else "branch_name"
    if any(f"v{version}" in arg for arg in cmd):
        return "rev_parse_tag"
    return "rev_parse"


def _categorize_git_command(cmd, version=""):
    """Categorize a git command list into a simple string label."""
    if "push" in cmd and "origin" in cmd and "refs/tags" not in cmd:
        return "push_branch"
    if "push" in cmd:
        return "push"
    if "fetch" in cmd:
        return "fetch"
    if "rev-parse" in cmd:
        return _categorize_rev_parse_command(cmd, version)
    if "remote" in cmd and "show" in cmd:
        return "remote_show"
    if "merge-base" in cmd:
        return "merge_base"
    if "ls-remote" in cmd:
        return "ls_remote"
    if "tag" in cmd and "--sort" in cmd:
        return "tag_sort"
    if "remote" in cmd and "get-url" in cmd:
        return "remote_url"
    return "other"


def test_release_with_bump_push_checks_branch_before_pushing_commit(mock_pyproject, monkeypatch):
    """Test that branch status is checked BEFORE pushing the bump commit.

    This ensures preflight validation catches problems (dirty tree, diverged branch)
    before any commits or pushes happen, preventing states that need manual recovery.
    """
    call_order = []

    def track_push(cmd, result):
        call_order.append("push_bump_commit")

    def track_fetch(cmd, result):
        call_order.append("fetch_for_branch_check")

    mock_git = _make_mock_git_for_bump_release(
        callbacks={"push_branch": track_push, "fetch": track_fetch},
    )

    def mock_bump_command(options):
        import tomlkit

        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())
        data["project"]["version"] = "1.2.4"
        with open("pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(data))

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git),
        patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command),
    ):
        release_command(bump_type="PATCH", push=True, non_interactive=True)

    # Branch status check (fetch) must happen BEFORE bump commit push
    assert "fetch_for_branch_check" in call_order, "Branch status should be checked"
    assert "push_bump_commit" in call_order, "Bump commit should be pushed to remote"
    fetch_idx = call_order.index("fetch_for_branch_check")
    push_idx = call_order.index("push_bump_commit")
    assert fetch_idx < push_idx, (
        f"Branch status check (index {fetch_idx}) should happen before bump commit push (index {push_idx})"
    )


def test_release_with_bump_dry_run_does_not_push_commit(mock_pyproject, monkeypatch):
    """Test that --dry-run does NOT push the bump commit to remote."""
    git_push_calls = []

    def track_push(cmd, result):
        git_push_calls.append(cmd)

    mock_git = _make_mock_git_for_bump_release(
        previous_tags="",
        callbacks={"push_branch": track_push, "push": track_push},
    )

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git),
        patch("rhiza_tools.commands.release.bump_command"),
    ):
        release_command(bump_type="PATCH", push=True, dry_run=True)

    # In dry-run mode, no branch push should happen (only tag-related pushes are simulated)
    branch_pushes = [cmd for cmd in git_push_calls if "refs/tags" not in cmd]
    assert len(branch_pushes) == 0, "Dry-run should not push bump commit to remote"


def test_push_tag_dry_run_with_tag_details(monkeypatch):
    """Test push_tag in dry-run mode shows tag details."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        if "show" in cmd:
            result.stdout = "abc123 Fix bug in parser"
        else:
            result.stdout = ""
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        push_tag("v1.0.0", dry_run=True)
        # Should complete without errors


def test_validate_tag_state_with_tag_details(mock_pyproject, monkeypatch):
    """Test _validate_tag_state shows tag details when available."""
    from rhiza_tools.commands.release import _validate_tag_state

    def mock_check_tag_exists(tag):
        return (True, False)  # Exists locally, not remotely

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        if "show" in cmd and "--format" in cmd:
            result.stdout = "abc123def|2024-01-15|Fix critical bug"
        else:
            result.stdout = ""
        return result

    with (
        patch("rhiza_tools.commands.release.check_tag_exists", side_effect=mock_check_tag_exists),
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
    ):
        _validate_tag_state("v1.2.3", "1.2.3")
        # Should complete and show tag details


def test_validate_tag_state_git_show_fails(mock_pyproject, monkeypatch):
    """Test _validate_tag_state when git show fails."""
    from rhiza_tools.commands.release import _validate_tag_state

    def mock_check_tag_exists(tag):
        return (True, False)  # Exists locally, not remotely

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        if "show" in cmd:
            result.returncode = 1  # Fail
            result.stdout = ""
        else:
            result.returncode = 0
            result.stdout = ""
        return result

    with (
        patch("rhiza_tools.commands.release.check_tag_exists", side_effect=mock_check_tag_exists),
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
    ):
        _validate_tag_state("v1.2.3", "1.2.3")
        # Should complete without showing tag details


def test_get_bump_type_interactively_eoferror(monkeypatch):
    """Test _get_bump_type_interactively handles EOFError."""
    from rhiza_tools.commands.release import _get_bump_type_interactively

    # Mock questionary to raise EOFError
    with patch("questionary.confirm") as mock_confirm:
        mock_confirm.return_value.ask.side_effect = EOFError

        should_bump, bump_type = _get_bump_type_interactively(False, None, False, language=Language.PYTHON)

        assert should_bump is False
        assert bump_type is None


def test_perform_version_bump_dry_run(mock_pyproject, monkeypatch):
    """Test _perform_version_bump in dry-run mode returns new version."""
    from rhiza_tools.commands.release import _perform_version_bump

    bump_called = {"called": False}

    def mock_bump_command(options):
        bump_called["called"] = True

    with patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command):
        new_version = _perform_version_bump("1.3.0", dry_run=True, language=Language.PYTHON)

    assert bump_called["called"]
    assert new_version == "1.3.0"


def test_show_commits_since_last_tag_with_commits(monkeypatch):
    """Test _show_commits_since_last_tag with actual commits."""
    from rhiza_tools.commands.release import _show_commits_since_last_tag

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0

        if "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.3\nv1.2.2\nv1.2.1"
        elif "log" in cmd:
            # Return more than 10 commits to test the truncation
            commits = "\n".join([f"abc{i:04d} Commit message {i}" for i in range(15)])
            result.stdout = commits
        else:
            result.stdout = ""

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        _show_commits_since_last_tag("v1.2.3")
        # Should complete and show commits


def test_show_commits_since_last_tag_no_tags(monkeypatch):
    """Test _show_commits_since_last_tag when git tag command fails."""
    from rhiza_tools.commands.release import _show_commits_since_last_tag

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        _show_commits_since_last_tag("v1.2.3")
        # Should complete without showing anything


def test_show_commits_since_last_tag_no_previous_tags(monkeypatch):
    """Test _show_commits_since_last_tag when there's only one tag."""
    from rhiza_tools.commands.release import _show_commits_since_last_tag

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0

        if "tag" in cmd:
            result.stdout = "v1.2.3"  # Only current tag
        else:
            result.stdout = ""

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        _show_commits_since_last_tag("v1.2.3")
        # Should complete without showing commits


def test_push_tag_with_ssh_url(monkeypatch):
    """Test push_tag with SSH repository URL."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        if "get-url" in cmd:
            result.stdout = "git@github.com:user/repo.git"
        else:
            result.stdout = ""
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        push_tag("v1.0.0", dry_run=False)
        # Should complete and show GitHub Actions URL


def test_push_tag_with_non_github_url(monkeypatch):
    """Test push_tag with non-GitHub repository URL."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        if "get-url" in cmd:
            result.stdout = "https://gitlab.com/user/repo.git"
        else:
            result.stdout = ""
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        push_tag("v1.0.0", dry_run=False)
        # Should complete without showing GitHub Actions URL


# ──────────────────────────────────────────────
# Preflight Validation Tests
# ──────────────────────────────────────────────


class TestReleasePreflightValidation:
    """Tests for preflight validation in release_command.

    These tests verify that all validations (repo state, tag availability)
    happen BEFORE any destructive operations (bump, commit, push).
    """

    def test_preflight_checks_repo_state_before_bump(self, mock_pyproject, monkeypatch):
        """Repository state check should block release before any bump happens."""
        bump_called = {"called": False}

        def mock_bump_command(options):
            bump_called["called"] = True

        def mock_run_git_command(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""

            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "remote" in cmd and "show" in cmd:
                result.stdout = "* remote origin\n  HEAD branch: main\n"
            elif "status" in cmd and "--porcelain" in cmd:
                result.stdout = " M dirty-file.txt\n"  # Dirty working tree
            elif "symbolic-full-name" in cmd:
                result.stdout = "origin/main"
            elif "rev-parse" in cmd or "merge-base" in cmd:
                result.stdout = "abc123"

            return result

        with (
            patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
            patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command),
            pytest.raises(typer.Exit),
        ):
            release_command(bump_type="PATCH", push=True, non_interactive=True)

        # Bump should NOT have been called since repo was dirty
        assert not bump_called["called"], "Bump should not be called when repo state is dirty"

    def test_preflight_checks_tag_availability_before_bump(self, mock_pyproject, monkeypatch):
        """Tag conflict on remote should block release before any bump happens."""
        bump_called = {"called": False}

        def mock_bump_command(options):
            bump_called["called"] = True

        def mock_run_git_command(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""

            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "remote" in cmd and "show" in cmd:
                result.stdout = "* remote origin\n  HEAD branch: main\n"
            elif "status" in cmd and "--porcelain" in cmd:
                result.stdout = ""  # Clean tree
            elif "symbolic-full-name" in cmd:
                result.stdout = "origin/main"
            elif "rev-parse" in cmd or "merge-base" in cmd:
                result.stdout = "abc123"
            elif "ls-remote" in cmd and "--tags" in cmd:
                result.returncode = 0  # Tag exists remotely (conflict!)

            return result

        with (
            patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
            patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command),
            pytest.raises(typer.Exit),
        ):
            release_command(bump_type="PATCH", push=True, non_interactive=True)

        # Bump should NOT have been called since tag already exists on remote
        assert not bump_called["called"], "Bump should not be called when tag already exists on remote"

    def test_preflight_tag_check_skipped_in_dry_run(self, mock_pyproject, monkeypatch):
        """Tag preflight check is skipped in dry-run mode (no destructive ops)."""
        mock_git = _make_mock_git_for_bump_release(
            tag_exists_remotely=False,
            previous_tags="",
        )

        with (
            patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git),
            patch("rhiza_tools.commands.release.bump_command"),
        ):
            # Should complete without error in dry-run
            release_command(bump_type="PATCH", push=True, dry_run=True)

    def test_preflight_allows_release_when_tag_available(self, mock_pyproject, monkeypatch):
        """Release proceeds when preflight confirms tag is available on remote."""
        bump_called = {"called": False}

        def mock_bump_command(options):
            bump_called["called"] = True
            import tomlkit

            with open("pyproject.toml") as f:
                data = tomlkit.parse(f.read())
            data["project"]["version"] = "1.2.4"
            with open("pyproject.toml", "w") as f:
                f.write(tomlkit.dumps(data))

        mock_git = _make_mock_git_for_bump_release(
            tag_exists_remotely=False,
        )

        with (
            patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git),
            patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command),
        ):
            release_command(bump_type="PATCH", push=True, non_interactive=True)

        assert bump_called["called"], "Bump should proceed when tag is available"


# ──────────────────────────────────────────────
# Multi-Language Support Tests
# ──────────────────────────────────────────────


@pytest.fixture
def mock_go_project(tmp_path, monkeypatch):
    """Create a temporary Go project with go.mod and VERSION files."""
    (tmp_path / "go.mod").write_text("module example.com/myproject\n\ngo 1.21\n")
    (tmp_path / "VERSION").write_text("1.2.3\n")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_release_command_go_project_dry_run(mock_go_project, monkeypatch):
    """Test release_command with a Go project in dry-run mode."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1  # Tag doesn't exist remotely
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.2\nv1.2.1"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        # Auto-detect should find Go project
        release_command(dry_run=True, non_interactive=True)


def test_release_command_go_project_explicit_language(mock_go_project, monkeypatch):
    """Test release_command with Go language explicitly specified."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.3" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.2\nv1.2.1"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        release_command(dry_run=True, non_interactive=True, language=Language.GO)


def test_release_command_no_project_files(tmp_path, monkeypatch):
    """Test release_command when no supported project files are found."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(typer.Exit):
        release_command()


def test_release_command_go_with_bump(mock_go_project, monkeypatch):
    """Test release_command with a Go project with bump type."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.4" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd or "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.3\nv1.2.2"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    bump_called = {"called": False, "language": None}

    def mock_bump_command(options):
        bump_called["called"] = True
        bump_called["language"] = options.language
        # Update VERSION file
        (mock_go_project / "VERSION").write_text("1.2.4\n")

    with (
        patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command),
        patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command),
    ):
        release_command(bump_type="PATCH", push=True, dry_run=True, language=Language.GO)

    assert bump_called["called"]
    assert bump_called["language"] == Language.GO
