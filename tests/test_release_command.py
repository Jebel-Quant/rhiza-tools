"""Tests for release command in rhiza_tools.commands.release."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import typer

from rhiza_tools.commands.release import (
    check_branch_status,
    check_clean_working_tree,
    check_tag_exists,
    create_tag,
    get_current_version,
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


def test_create_tag_unsigned(monkeypatch):
    """Test creating an unsigned tag."""
    mock_run_git = MagicMock()
    mock_run_git.return_value.returncode = 1  # No signing key

    with patch("rhiza_tools.commands.release.run_git_command", mock_run_git):
        create_tag("v1.0.0", "Release v1.0.0", dry_run=False)

        # Should call git tag -a
        calls = mock_run_git.call_args_list
        tag_call = [c for c in calls if "tag" in c[0][0]]
        assert len(tag_call) > 0
        assert "-a" in tag_call[-1][0][0]


def test_create_tag_signed(monkeypatch):
    """Test creating a signed tag."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        if "user.signingkey" in cmd:
            result.returncode = 0  # Signing key configured
        else:
            result.returncode = 0
        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        create_tag("v1.0.0", "Release v1.0.0", dry_run=False)


def test_create_tag_dry_run(monkeypatch):
    """Test creating a tag in dry-run mode."""
    mock_run_git = MagicMock()
    mock_run_git.return_value.returncode = 1  # No signing key

    with patch("rhiza_tools.commands.release.run_git_command", mock_run_git):
        create_tag("v1.0.0", "Release v1.0.0", dry_run=True)

        # Should not create actual tag in dry-run
        tag_calls = [c for c in mock_run_git.call_args_list if "tag" in c[0][0] and "-a" in c[0][0]]
        assert len(tag_calls) == 0


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
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd:
            result.returncode = 1  # Tag doesn't exist
        elif "describe" in cmd:
            result.returncode = 1  # No previous tags
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"

        return result

    with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_run_git_command):
        release_command(dry_run=True)  # Should complete without errors


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
