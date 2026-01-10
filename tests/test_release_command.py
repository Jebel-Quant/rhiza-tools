"""Tests for release command implementation."""

from unittest.mock import MagicMock, patch

import pytest
import tomlkit
import typer

from rhiza_tools.commands.release import (
    check_git_status,
    check_tag_exists,
    create_tag,
    get_current_branch,
    get_current_version,
    get_default_branch,
    get_last_tag,
    is_gpg_signing_enabled,
    push_tag,
    release_command,
    run_command,
)


@pytest.fixture
def mock_git_repo(tmp_path, monkeypatch):
    """Create a mock git repository environment."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create pyproject.toml
    pyproject_content = {
        "project": {
            "name": "test-project",
            "version": "1.2.3",
        }
    }
    with open("pyproject.toml", "w") as f:
        f.write(tomlkit.dumps(pyproject_content))

    return tmp_path


def test_get_current_version(mock_git_repo):
    """Test reading version from pyproject.toml."""
    version = get_current_version()
    assert version == "1.2.3"


def test_get_current_version_missing_file(tmp_path, monkeypatch):
    """Test get_current_version when pyproject.toml is missing."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(typer.Exit):
        get_current_version()


def test_run_command_success():
    """Test running a successful command."""
    result = run_command(["echo", "test"])
    assert result.returncode == 0
    assert result.stdout.strip() == "test"


def test_run_command_failure():
    """Test running a failed command."""
    with pytest.raises(typer.Exit):
        run_command(["false"])


@patch("rhiza_tools.commands.release.run_command")
def test_check_git_status_clean(mock_run):
    """Test check_git_status with clean working tree."""
    mock_run.return_value = MagicMock(stdout="", returncode=0)

    # Should not raise
    check_git_status()

    mock_run.assert_called_once()


@patch("rhiza_tools.commands.release.run_command")
def test_check_git_status_dirty(mock_run):
    """Test check_git_status with uncommitted changes."""
    mock_run.return_value = MagicMock(stdout=" M file.txt\n", returncode=0)

    with pytest.raises(typer.Exit):
        check_git_status()


@patch("rhiza_tools.commands.release.run_command")
def test_get_current_branch(mock_run):
    """Test getting current branch name."""
    mock_run.return_value = MagicMock(stdout="main\n", returncode=0)

    branch = get_current_branch()
    assert branch == "main"


@patch("rhiza_tools.commands.release.run_command")
def test_get_default_branch(mock_run):
    """Test getting default branch from remote."""
    mock_run.return_value = MagicMock(
        stdout="* remote origin\n  HEAD branch: main\n  Remote branches:\n",
        returncode=0
    )

    branch = get_default_branch()
    assert branch == "main"


@patch("rhiza_tools.commands.release.run_command")
def test_check_tag_exists_local_and_remote(mock_run):
    """Test checking if tag exists both locally and remotely."""
    # First call: local check (exists)
    # Second call: remote check (exists)
    mock_run.side_effect = [
        MagicMock(returncode=0),  # local exists
        MagicMock(returncode=0),  # remote exists
    ]

    exists_locally, exists_remotely = check_tag_exists("v1.2.3")
    assert exists_locally is True
    assert exists_remotely is True


@patch("rhiza_tools.commands.release.run_command")
def test_check_tag_exists_neither(mock_run):
    """Test checking if tag exists when it doesn't exist anywhere."""
    mock_run.side_effect = [
        MagicMock(returncode=1),  # local doesn't exist
        MagicMock(returncode=1),  # remote doesn't exist
    ]

    exists_locally, exists_remotely = check_tag_exists("v1.2.3")
    assert exists_locally is False
    assert exists_remotely is False


@patch("rhiza_tools.commands.release.run_command")
def test_is_gpg_signing_enabled_via_signingkey(mock_run):
    """Test GPG signing detection via user.signingkey."""
    mock_run.return_value = MagicMock(returncode=0, stdout="ABCD1234\n")

    assert is_gpg_signing_enabled() is True


@patch("rhiza_tools.commands.release.run_command")
def test_is_gpg_signing_enabled_via_gpgsign(mock_run):
    """Test GPG signing detection via commit.gpgsign."""
    mock_run.side_effect = [
        MagicMock(returncode=1, stdout=""),  # no signingkey
        MagicMock(returncode=0, stdout="true\n"),  # gpgsign=true
    ]

    assert is_gpg_signing_enabled() is True


@patch("rhiza_tools.commands.release.run_command")
def test_is_gpg_signing_disabled(mock_run):
    """Test GPG signing detection when disabled."""
    mock_run.side_effect = [
        MagicMock(returncode=1, stdout=""),  # no signingkey
        MagicMock(returncode=0, stdout="false\n"),  # gpgsign=false
    ]

    assert is_gpg_signing_enabled() is False


@patch("rhiza_tools.commands.release.run_command")
def test_get_last_tag(mock_run):
    """Test getting last tag."""
    mock_run.return_value = MagicMock(returncode=0, stdout="v1.2.2\n")

    tag = get_last_tag()
    assert tag == "v1.2.2"


@patch("rhiza_tools.commands.release.run_command")
def test_get_last_tag_no_tags(mock_run):
    """Test getting last tag when no tags exist."""
    mock_run.return_value = MagicMock(returncode=1, stdout="")

    tag = get_last_tag()
    assert tag == ""


@patch("rhiza_tools.commands.release.prompt_continue")
@patch("rhiza_tools.commands.release.run_command")
@patch("rhiza_tools.commands.release.is_gpg_signing_enabled")
def test_create_tag_signed(mock_gpg, mock_run, mock_prompt):
    """Test creating a signed tag."""
    mock_gpg.return_value = True
    mock_run.return_value = MagicMock(returncode=0)

    create_tag("v1.2.3", "1.2.3")

    # Check that git tag -s was called
    assert any(
        call[0][0] == ["git", "tag", "-s", "v1.2.3", "-m", "Release v1.2.3"]
        for call in mock_run.call_args_list
    )


@patch("rhiza_tools.commands.release.prompt_continue")
@patch("rhiza_tools.commands.release.run_command")
@patch("rhiza_tools.commands.release.is_gpg_signing_enabled")
def test_create_tag_unsigned(mock_gpg, mock_run, mock_prompt):
    """Test creating an unsigned tag."""
    mock_gpg.return_value = False
    mock_run.return_value = MagicMock(returncode=0)

    create_tag("v1.2.3", "1.2.3")

    # Check that git tag -a was called
    assert any(
        call[0][0] == ["git", "tag", "-a", "v1.2.3", "-m", "Release v1.2.3"]
        for call in mock_run.call_args_list
    )


@patch("rhiza_tools.commands.release.prompt_continue")
@patch("rhiza_tools.commands.release.get_last_tag")
@patch("rhiza_tools.commands.release.run_command")
def test_push_tag(mock_run, mock_last_tag, mock_prompt):
    """Test pushing a tag to remote."""
    mock_last_tag.return_value = "v1.2.2"
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="5\n"),  # commit count
        MagicMock(returncode=0),  # git push
        MagicMock(returncode=0, stdout="git@github.com:user/repo.git\n"),  # get-url
    ]

    push_tag("v1.2.3")

    # Verify git push was called with correct args
    push_call = [c for c in mock_run.call_args_list if "push" in str(c)]
    assert len(push_call) > 0


@patch("rhiza_tools.commands.release.check_upstream_status")
@patch("rhiza_tools.commands.release.check_branch")
@patch("rhiza_tools.commands.release.check_git_status")
@patch("rhiza_tools.commands.release.get_current_branch")
@patch("rhiza_tools.commands.release.check_tag_exists")
@patch("rhiza_tools.commands.release.create_tag")
@patch("rhiza_tools.commands.release.push_tag")
def test_release_command_dry_run(
    mock_push, mock_create, mock_check_tag, mock_branch, mock_status, mock_check_branch, mock_upstream, mock_git_repo
):
    """Test release command in dry-run mode."""
    mock_branch.return_value = "main"

    # Should not raise and should not call actual operations
    release_command(dry_run=True)

    # Verify no actual operations were performed
    mock_status.assert_not_called()
    mock_check_branch.assert_not_called()
    mock_upstream.assert_not_called()
    mock_check_tag.assert_not_called()
    mock_create.assert_not_called()
    mock_push.assert_not_called()


@patch("rhiza_tools.commands.release.push_tag")
@patch("rhiza_tools.commands.release.create_tag")
@patch("rhiza_tools.commands.release.check_tag_exists")
@patch("rhiza_tools.commands.release.check_upstream_status")
@patch("rhiza_tools.commands.release.check_branch")
@patch("rhiza_tools.commands.release.check_git_status")
@patch("rhiza_tools.commands.release.get_current_branch")
def test_release_command_tag_exists_remotely(
    mock_branch, mock_status, mock_check_branch, mock_upstream, mock_check_tag, mock_create, mock_push, mock_git_repo
):
    """Test release command when tag already exists on remote."""
    mock_branch.return_value = "main"
    mock_check_tag.return_value = (False, True)  # exists remotely

    with pytest.raises(typer.Exit):
        release_command(dry_run=False)

    # Verify tag creation and push were not called
    mock_create.assert_not_called()
    mock_push.assert_not_called()


@patch("rhiza_tools.commands.release.push_tag")
@patch("rhiza_tools.commands.release.prompt_continue")
@patch("rhiza_tools.commands.release.check_tag_exists")
@patch("rhiza_tools.commands.release.check_upstream_status")
@patch("rhiza_tools.commands.release.check_branch")
@patch("rhiza_tools.commands.release.check_git_status")
@patch("rhiza_tools.commands.release.get_current_branch")
def test_release_command_tag_exists_locally(
    mock_branch, mock_status, mock_check_branch, mock_upstream, mock_check_tag, mock_prompt, mock_push, mock_git_repo
):
    """Test release command when tag already exists locally."""
    mock_branch.return_value = "main"
    mock_check_tag.return_value = (True, False)  # exists locally only

    release_command(dry_run=False)

    # Verify prompt was called and push was called (but not create)
    mock_prompt.assert_called()
    mock_push.assert_called_once()


@patch("rhiza_tools.commands.release.push_tag")
@patch("rhiza_tools.commands.release.create_tag")
@patch("rhiza_tools.commands.release.check_tag_exists")
@patch("rhiza_tools.commands.release.check_upstream_status")
@patch("rhiza_tools.commands.release.check_branch")
@patch("rhiza_tools.commands.release.check_git_status")
@patch("rhiza_tools.commands.release.get_current_branch")
def test_release_command_success(
    mock_branch, mock_status, mock_check_branch, mock_upstream, mock_check_tag, mock_create, mock_push, mock_git_repo
):
    """Test successful release command execution."""
    mock_branch.return_value = "main"
    mock_check_tag.return_value = (False, False)  # doesn't exist

    release_command(dry_run=False)

    # Verify all steps were called
    mock_status.assert_called_once()
    mock_check_branch.assert_called_once_with("main")
    mock_upstream.assert_called_once_with("main")
    mock_check_tag.assert_called_once_with("v1.2.3")
    mock_create.assert_called_once_with("v1.2.3", "1.2.3")
    mock_push.assert_called_once_with("v1.2.3")
