"""Tests for release command in rhiza_tools.commands.release."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
import typer

from rhiza_tools.commands.bump import BumpOptions, get_current_version
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
    version = get_current_version()
    assert version == "1.2.3"


def test_get_current_version_missing_file(tmp_path, monkeypatch):
    """Test error when pyproject.toml is missing."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(typer.Exit):
        get_current_version()


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

    with patch("rhiza_tools.commands.release.run_git_command", return_value=mock_result):
        with pytest.raises(typer.Exit):
            check_clean_working_tree()


def test_check_branch_status_up_to_date(monkeypatch):
    """Test check_branch_status when branch is up-to-date."""
    commit_hash = "abc123"

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        if "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "rev-parse" in cmd:
            result.stdout = commit_hash
        elif "merge-base" in cmd:
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

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with pytest.raises(typer.Exit):
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

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with pytest.raises(typer.Exit):
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

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with pytest.raises(typer.Exit):
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

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with pytest.raises(typer.Exit):
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
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

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd and "--tags" in cmd:
            result.returncode = 1  # Tag doesn't exist remotely

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with pytest.raises(typer.Exit):
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd and "--tags" in cmd:
            result.returncode = 0  # Tag exists remotely

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with pytest.raises(typer.Exit):
            release_command()


def test_check_branch_status_no_upstream(monkeypatch):
    """Test error when no upstream branch is configured."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        if "--symbolic-full-name" in cmd:
            result.returncode = 1  # No upstream
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with pytest.raises(typer.Exit):
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

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with pytest.raises(typer.Exit):
            check_branch_status("main")


def test_get_default_branch_no_head_branch(monkeypatch):
    """Test error when default branch cannot be found in remote output."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "* remote origin\n  some other info\n"  # No HEAD branch line
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with pytest.raises(typer.Exit):
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.2\nv1.2.1"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with patch("typer.confirm", return_value=False):
            with pytest.raises(typer.Exit) as exc_info:
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with patch("typer.confirm", return_value=False):
            with pytest.raises(typer.Exit) as exc_info:
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
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

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command):
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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
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

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with patch("rhiza_tools.commands.release.push_tag", side_effect=mock_push_tag):
            release_command(push=True)

    assert push_called["called"]


def test_release_non_interactive_with_bump(mock_pyproject, monkeypatch):
    """Test release in non-interactive mode with bump."""
    git_push_calls = []

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "push" in cmd:
            git_push_calls.append(cmd)
        elif "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "main"
        elif "symbolic-full-name" in cmd:
            result.stdout = "origin/main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.4" in arg for arg in cmd):
            result.stdout = "abc123"
            result.returncode = 0
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.3\nv1.2.2"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

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

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command):
            release_command(bump_type="MINOR", push=True, non_interactive=True)

    assert bump_called["called"]
    # Verify the bump commit was pushed to remote
    assert any("push" in cmd and "origin" in cmd and "main" in cmd for cmd in git_push_calls), (
        "Expected bump commit to be pushed to remote with 'git push origin main'"
    )


def test_release_with_bump_push_pushes_commit_before_branch_check(mock_pyproject, monkeypatch):
    """Test that --push pushes the bump commit to remote before branch status check."""
    call_order = []

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "push" in cmd and "origin" in cmd and "refs/tags" not in cmd:
            call_order.append("push_bump_commit")
        elif "fetch" in cmd:
            call_order.append("fetch_for_branch_check")
        elif "rev-parse" in cmd and "--abbrev-ref" in cmd:
            if "--symbolic-full-name" in cmd:
                result.stdout = "origin/main"
            else:
                result.stdout = "main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd and any("v1.2.4" in arg for arg in cmd):
            result.stdout = "abc123"
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = "v1.2.3\nv1.2.2"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    def mock_bump_command(options):
        import tomlkit

        with open("pyproject.toml") as f:
            data = tomlkit.parse(f.read())
        data["project"]["version"] = "1.2.4"
        with open("pyproject.toml", "w") as f:
            f.write(tomlkit.dumps(data))

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command):
            release_command(bump_type="PATCH", push=True, non_interactive=True)

    # Bump commit must be pushed BEFORE git fetch (which is the first step of check_branch_status)
    assert "push_bump_commit" in call_order, "Bump commit should be pushed to remote"
    assert "fetch_for_branch_check" in call_order, "Branch status should be checked"
    push_idx = call_order.index("push_bump_commit")
    fetch_idx = call_order.index("fetch_for_branch_check")
    assert push_idx < fetch_idx, (
        f"Bump commit push (index {push_idx}) should happen before branch status check (index {fetch_idx})"
    )


def test_release_with_bump_dry_run_does_not_push_commit(mock_pyproject, monkeypatch):
    """Test that --dry-run does NOT push the bump commit to remote."""
    git_push_calls = []

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "push" in cmd:
            git_push_calls.append(cmd)
        elif "rev-parse" in cmd and "--abbrev-ref" in cmd:
            if "--symbolic-full-name" in cmd:
                result.stdout = "origin/main"
            else:
                result.stdout = "main"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = ""
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        with patch("rhiza_tools.commands.release.bump_command"):
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

    with patch("rhiza_tools.commands.release.check_tag_exists", side_effect=mock_check_tag_exists):
        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
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

    with patch("rhiza_tools.commands.release.check_tag_exists", side_effect=mock_check_tag_exists):
        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
            _validate_tag_state("v1.2.3", "1.2.3")
            # Should complete without showing tag details


def test_get_bump_type_interactively_eoferror(monkeypatch):
    """Test _get_bump_type_interactively handles EOFError."""
    from rhiza_tools.commands.release import _get_bump_type_interactively

    # Mock questionary to raise EOFError
    with patch("questionary.confirm") as mock_confirm:
        mock_confirm.return_value.ask.side_effect = EOFError

        should_bump, bump_type = _get_bump_type_interactively(False, None, False)

        assert should_bump is False
        assert bump_type is None


def test_perform_version_bump_dry_run(mock_pyproject, monkeypatch):
    """Test _perform_version_bump in dry-run mode returns new version."""
    from rhiza_tools.commands.release import _perform_version_bump

    bump_called = {"called": False}

    def mock_bump_command(options):
        bump_called["called"] = True

    with patch("rhiza_tools.commands.release.bump_command", side_effect=mock_bump_command):
        new_version = _perform_version_bump("1.3.0", dry_run=True)

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
