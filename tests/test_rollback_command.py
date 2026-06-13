"""Tests for the rollback command."""

from unittest.mock import MagicMock, patch

import pytest
import typer

import rhiza_tools.commands.rollback as rollback_mod
import rhiza_tools.commands.rollback_git as rollback_git_mod
from rhiza_tools.commands.rollback import (
    RollbackOptions,
    _confirm_rollback,
    _delete_local_tag,
    _delete_remote_tag,
    _get_previous_version_from_tags,
    _get_recent_tags,
    _get_tag_commit,
    _get_tag_details,
    _is_bump_commit,
    _push_revert,
    _revert_bump_commit,
    _select_tag_interactively,
    _show_rollback_plan,
    _validate_rollback_preconditions,
    rollback_command,
)

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


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


# ──────────────────────────────────────────────
# Unit tests: _get_recent_tags
# ──────────────────────────────────────────────


class TestGetRecentTags:
    """Tests for _get_recent_tags."""

    def test_returns_tags(self):
        """Should return recent version tags."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "v1.2.3\nv1.2.2\nv1.2.1\n"

        with patch.object(rollback_mod, "run_git_command", return_value=mock_result):
            tags = _get_recent_tags()
            assert tags == ["v1.2.3", "v1.2.2", "v1.2.1"]

    def test_returns_empty_on_failure(self):
        """Should return empty list when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch.object(rollback_mod, "run_git_command", return_value=mock_result):
            tags = _get_recent_tags()
            assert tags == []

    def test_returns_empty_on_no_tags(self):
        """Should return empty list when no tags exist."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch.object(rollback_mod, "run_git_command", return_value=mock_result):
            tags = _get_recent_tags()
            assert tags == []

    def test_respects_limit(self):
        """Should limit number of tags returned."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "v1.2.3\nv1.2.2\nv1.2.1\nv1.2.0\nv1.1.0\n"

        with patch.object(rollback_mod, "run_git_command", return_value=mock_result):
            tags = _get_recent_tags(limit=2)
            assert tags == ["v1.2.3", "v1.2.2"]


# ──────────────────────────────────────────────
# Unit tests: _select_tag_interactively
# ──────────────────────────────────────────────


class TestSelectTagInteractively:
    """Tests for _select_tag_interactively."""

    def test_exits_on_empty_tags(self):
        """Should exit with code 1 when no tags available."""
        with pytest.raises(typer.Exit) as exc_info:
            _select_tag_interactively([])
        assert exc_info.value.exit_code == 1

    def test_returns_selected_tag(self, monkeypatch):
        """Should return the tag selected by user."""

        class MockQuestion:
            def ask(self):
                return "v1.2.3 (local, remote)"

        def mock_check_tag_exists(tag):
            return True, True

        monkeypatch.setattr(rollback_mod.qs, "select", lambda *a, **kw: MockQuestion())

        with patch.object(rollback_mod, "check_tag_exists", side_effect=mock_check_tag_exists):
            result = _select_tag_interactively(["v1.2.3", "v1.2.2"])
            assert result == "v1.2.3"

    def test_exits_on_cancel(self, monkeypatch):
        """Should exit with code 0 when user cancels."""

        class MockQuestion:
            def ask(self):
                return None

        def mock_check_tag_exists(tag):
            return True, False

        monkeypatch.setattr(rollback_mod.qs, "select", lambda *a, **kw: MockQuestion())

        with (
            patch.object(rollback_mod, "check_tag_exists", side_effect=mock_check_tag_exists),
            pytest.raises(typer.Exit) as exc_info,
        ):
            _select_tag_interactively(["v1.2.3"])
        assert exc_info.value.exit_code == 0

    def test_handles_eof_error(self, monkeypatch):
        """Should exit on EOFError (non-interactive environment)."""

        def mock_check_tag_exists(tag):
            return True, False

        def mock_select(*args, **kwargs):
            raise EOFError

        monkeypatch.setattr(rollback_mod.qs, "select", mock_select)

        with (
            patch.object(rollback_mod, "check_tag_exists", side_effect=mock_check_tag_exists),
            pytest.raises(typer.Exit) as exc_info,
        ):
            _select_tag_interactively(["v1.2.3"])
        assert exc_info.value.exit_code == 1


# ──────────────────────────────────────────────
# Unit tests: _get_tag_commit
# ──────────────────────────────────────────────


class TestGetTagCommit:
    """Tests for _get_tag_commit."""

    def test_returns_commit_hash(self):
        """Should return the commit hash."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123def456\n"

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            commit = _get_tag_commit("v1.2.3")
            assert commit == "abc123def456"

    def test_returns_none_on_failure(self):
        """Should return None when tag doesn't exist."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            commit = _get_tag_commit("v9.9.9")
            assert commit is None


# ──────────────────────────────────────────────
# Unit tests: _get_tag_details
# ──────────────────────────────────────────────


class TestGetTagDetails:
    """Tests for _get_tag_details."""

    def test_returns_details(self):
        """Should return tag details dictionary."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123|2025-01-01 12:00:00|Bump version: 1.2.2 → 1.2.3"

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            details = _get_tag_details("v1.2.3")
            assert details["hash"] == "abc123"
            assert details["date"] == "2025-01-01 12:00:00"
            assert details["message"] == "Bump version: 1.2.2 → 1.2.3"

    def test_returns_empty_on_failure(self):
        """Should return empty dict when command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            details = _get_tag_details("v9.9.9")
            assert details == {}


# ──────────────────────────────────────────────
# Unit tests: _is_bump_commit
# ──────────────────────────────────────────────


class TestIsBumpCommit:
    """Tests for _is_bump_commit."""

    def test_detects_bump_commit(self):
        """Should detect bump commit messages."""
        bump_messages = [
            "Bump version: 1.2.2 → 1.2.3",
            "bump: 1.2.3",
            "Version bump to 2.0.0",
            "Release version 1.0.0",
            "chore: bump version",
        ]
        for msg in bump_messages:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = msg

            with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
                assert _is_bump_commit("v1.2.3"), f"Should detect: {msg}"

    def test_rejects_non_bump_commit(self):
        """Should reject non-bump commit messages."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Add new feature X"

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            assert not _is_bump_commit("v1.2.3")

    def test_returns_false_on_failure(self):
        """Should return False when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            assert not _is_bump_commit("v9.9.9")


# ──────────────────────────────────────────────
# Unit tests: _get_previous_version_from_tags
# ──────────────────────────────────────────────


class TestGetPreviousVersionFromTags:
    """Tests for _get_previous_version_from_tags."""

    def test_finds_previous_tag(self):
        """Should return the previous version tag."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "v1.2.3\nv1.2.2\nv1.2.1\n"

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            prev = _get_previous_version_from_tags("v1.2.3")
            assert prev == "v1.2.2"

    def test_returns_none_for_first_tag(self):
        """Should return None when there is no previous tag."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "v0.1.0\n"

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            prev = _get_previous_version_from_tags("v0.1.0")
            assert prev is None

    def test_returns_none_when_tag_not_found(self):
        """Should return None when current tag not in list."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "v1.2.3\nv1.2.2\n"

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            prev = _get_previous_version_from_tags("v9.9.9")
            assert prev is None

    def test_returns_none_on_failure(self):
        """Should return None when git command fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            prev = _get_previous_version_from_tags("v1.2.3")
            assert prev is None


# ──────────────────────────────────────────────
# Unit tests: _delete_local_tag
# ──────────────────────────────────────────────


class TestDeleteLocalTag:
    """Tests for _delete_local_tag."""

    def test_deletes_tag(self):
        """Should delete a local tag successfully."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            assert _delete_local_tag("v1.2.3", dry_run=False)

    def test_dry_run_does_not_delete(self):
        """Should not actually delete in dry-run mode."""
        with patch.object(rollback_git_mod, "run_git_command") as mock_cmd:
            assert _delete_local_tag("v1.2.3", dry_run=True)
            mock_cmd.assert_not_called()

    def test_handles_failure(self):
        """Should return False on failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error: tag 'v1.2.3' not found."

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            assert not _delete_local_tag("v1.2.3", dry_run=False)


# ──────────────────────────────────────────────
# Unit tests: _delete_remote_tag
# ──────────────────────────────────────────────


class TestDeleteRemoteTag:
    """Tests for _delete_remote_tag."""

    def test_deletes_tag(self):
        """Should delete a remote tag successfully."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            assert _delete_remote_tag("v1.2.3", dry_run=False)

    def test_dry_run_does_not_delete(self):
        """Should not actually delete in dry-run mode."""
        with patch.object(rollback_git_mod, "run_git_command") as mock_cmd:
            assert _delete_remote_tag("v1.2.3", dry_run=True)
            mock_cmd.assert_not_called()

    def test_handles_failure(self):
        """Should return False on failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error: unable to delete 'v1.2.3'"

        with patch.object(rollback_git_mod, "run_git_command", return_value=mock_result):
            assert not _delete_remote_tag("v1.2.3", dry_run=False)


# ──────────────────────────────────────────────
# Unit tests: _revert_bump_commit
# ──────────────────────────────────────────────


class TestRevertBumpCommit:
    """Tests for _revert_bump_commit."""

    def test_reverts_commit(self):
        """Should revert the bump commit."""
        mock_revert = MagicMock()
        mock_revert.returncode = 0

        def mock_run_git(cmd, check=True):
            if "revert" in cmd:
                return mock_revert
            return MagicMock(returncode=0, stdout="")

        with patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git):
            assert _revert_bump_commit("abc123def456", dry_run=False)

    def test_dry_run_does_not_revert(self):
        """Should not actually revert in dry-run mode."""
        mock_log = MagicMock()
        mock_log.returncode = 0
        mock_log.stdout = "Bump version: 1.2.2 → 1.2.3"

        def mock_run_git(cmd, check=True):
            if "log" in cmd:
                return mock_log
            return MagicMock(returncode=0, stdout="")

        with patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git):
            assert _revert_bump_commit("abc123def456", dry_run=True)

    def test_handles_revert_failure(self):
        """Should return False when revert fails."""
        mock_revert = MagicMock()
        mock_revert.returncode = 1
        mock_revert.stderr = "error: could not revert"

        def mock_run_git(cmd, check=True):
            if "revert" in cmd:
                return mock_revert
            return MagicMock(returncode=0, stdout="")

        with patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git):
            assert not _revert_bump_commit("abc123def456", dry_run=False)


# ──────────────────────────────────────────────
# Unit tests: _push_revert
# ──────────────────────────────────────────────


class TestPushRevert:
    """Tests for _push_revert."""

    def test_dry_run(self):
        """Should not push in dry-run mode."""
        with patch.object(rollback_mod, "run_git_command") as mock_cmd:
            assert _push_revert(dry_run=True, non_interactive=False)
            mock_cmd.assert_not_called()

    def test_non_interactive_pushes(self):
        """Should push without prompt in non-interactive mode."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(rollback_mod, "run_git_command", return_value=mock_result):
            assert _push_revert(dry_run=False, non_interactive=True)

    def test_user_declines_push(self, monkeypatch):
        """Should not push when user declines."""

        class MockConfirm:
            def ask(self):
                return False

        monkeypatch.setattr(rollback_mod.qs, "confirm", lambda *a, **kw: MockConfirm())

        # Should return True (not pushing is a valid outcome)
        assert _push_revert(dry_run=False, non_interactive=False)

    def test_push_failure(self):
        """Should return False on push failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error: failed to push"

        with patch.object(rollback_mod, "run_git_command", return_value=mock_result):
            assert not _push_revert(dry_run=False, non_interactive=True)


# ──────────────────────────────────────────────
# Unit tests: _confirm_rollback
# ──────────────────────────────────────────────


class TestConfirmRollback:
    """Tests for _confirm_rollback."""

    def test_non_interactive_returns_true(self):
        """Should return True in non-interactive mode."""
        assert _confirm_rollback(non_interactive=True)

    def test_user_confirms(self, monkeypatch):
        """Should return True when user confirms."""

        class MockConfirm:
            def ask(self):
                return True

        monkeypatch.setattr(rollback_mod.qs, "confirm", lambda *a, **kw: MockConfirm())
        assert _confirm_rollback(non_interactive=False)

    def test_user_declines(self, monkeypatch):
        """Should return False when user declines."""

        class MockConfirm:
            def ask(self):
                return False

        monkeypatch.setattr(rollback_mod.qs, "confirm", lambda *a, **kw: MockConfirm())
        assert not _confirm_rollback(non_interactive=False)

    def test_handles_eof_error(self, monkeypatch):
        """Should return True on EOFError."""

        def mock_confirm(*args, **kwargs):
            raise EOFError

        monkeypatch.setattr(rollback_mod.qs, "confirm", mock_confirm)
        assert _confirm_rollback(non_interactive=False)


# ──────────────────────────────────────────────
# Unit tests: _validate_rollback_preconditions
# ──────────────────────────────────────────────


class TestValidateRollbackPreconditions:
    """Tests for _validate_rollback_preconditions."""

    def test_tag_exists_locally(self):
        """Should pass when tag exists locally."""
        with patch.object(rollback_mod, "check_tag_exists", return_value=(True, False)):
            local, remote = _validate_rollback_preconditions("v1.2.3")
            assert local is True
            assert remote is False

    def test_tag_exists_remotely(self):
        """Should pass when tag exists remotely."""
        with patch.object(rollback_mod, "check_tag_exists", return_value=(False, True)):
            local, remote = _validate_rollback_preconditions("v1.2.3")
            assert local is False
            assert remote is True

    def test_tag_exists_both(self):
        """Should pass when tag exists both locally and remotely."""
        with patch.object(rollback_mod, "check_tag_exists", return_value=(True, True)):
            local, remote = _validate_rollback_preconditions("v1.2.3")
            assert local is True
            assert remote is True

    def test_tag_not_found(self):
        """Should exit when tag doesn't exist anywhere."""
        with (
            patch.object(rollback_mod, "check_tag_exists", return_value=(False, False)),
            pytest.raises(typer.Exit) as exc_info,
        ):
            _validate_rollback_preconditions("v9.9.9")
        assert exc_info.value.exit_code == 1


# ──────────────────────────────────────────────
# Unit tests: _show_rollback_plan
# ──────────────────────────────────────────────


class TestShowRollbackPlan:
    """Tests for _show_rollback_plan."""

    def test_shows_full_plan(self):
        """Should display full rollback plan without errors."""
        # Just confirming no exceptions are raised
        _show_rollback_plan(
            tag="v1.2.3",
            exists_locally=True,
            exists_remotely=True,
            revert_bump=True,
            is_bump=True,
            previous_tag="v1.2.2",
            tag_details={"hash": "abc123", "date": "2025-01-01", "message": "Bump version"},
        )

    def test_shows_partial_plan_local_only(self):
        """Should handle local-only tag."""
        _show_rollback_plan(
            tag="v1.2.3",
            exists_locally=True,
            exists_remotely=False,
            revert_bump=False,
            is_bump=False,
            previous_tag=None,
            tag_details={},
        )

    def test_shows_partial_plan_remote_only(self):
        """Should handle remote-only tag."""
        _show_rollback_plan(
            tag="v1.2.3",
            exists_locally=False,
            exists_remotely=True,
            revert_bump=False,
            is_bump=False,
            previous_tag="v1.2.2",
            tag_details={},
        )


# ──────────────────────────────────────────────
# Integration tests: rollback_command
# ──────────────────────────────────────────────


class TestRollbackCommand:
    """Integration tests for rollback_command."""

    def test_missing_pyproject(self, tmp_path, monkeypatch):
        """Should exit when pyproject.toml is missing."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(typer.Exit):
            rollback_command(RollbackOptions(tag="v1.2.3"))

    def test_tag_not_found(self, mock_pyproject):
        """Should exit when tag doesn't exist."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "main"
            if "rev-parse" in cmd and "v1.2.3" in cmd:
                result.returncode = 1
            if "ls-remote" in cmd:
                result.returncode = 1
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(False, False)),
            pytest.raises(typer.Exit) as exc_info,
        ):
            rollback_command(RollbackOptions(tag="v1.2.3", non_interactive=True))
        assert exc_info.value.exit_code == 1

    def test_dry_run_local_and_remote_tag(self, mock_pyproject):
        """Should preview rollback in dry-run mode."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "tag" in cmd and "--sort" in cmd:
                result.stdout = "v1.2.3\nv1.2.2\n"
            elif "show" in cmd:
                result.stdout = "abc123|2025-01-01|Bump version"
            elif "log" in cmd:
                result.stdout = "Some commit"
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(True, True)),
        ):
            rollback_command(RollbackOptions(tag="v1.2.3", dry_run=True, non_interactive=True))

    def test_dry_run_with_revert_bump(self, mock_pyproject):
        """Should preview rollback with bump revert in dry-run mode."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "tag" in cmd and "--sort" in cmd:
                result.stdout = "v1.2.3\nv1.2.2\n"
            elif "show" in cmd:
                result.stdout = "abc123|2025-01-01|Bump version: 1.2.2 → 1.2.3"
            elif "log" in cmd and "-1" in cmd:
                result.stdout = "Bump version: 1.2.2 → 1.2.3"
            elif "rev-list" in cmd:
                result.stdout = "abc123def456"
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(True, True)),
        ):
            rollback_command(RollbackOptions(tag="v1.2.3", revert_bump=True, dry_run=True, non_interactive=True))

    def test_non_interactive_rollback(self, mock_pyproject):
        """Should rollback without prompts in non-interactive mode."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "tag" in cmd and "--sort" in cmd:
                result.stdout = "v1.2.3\nv1.2.2\n"
            elif "show" in cmd:
                result.stdout = "abc123|2025-01-01|Some commit"
            elif "log" in cmd:
                result.stdout = "Some commit"
            elif "push" in cmd:
                result.returncode = 0
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(True, True)),
        ):
            rollback_command(RollbackOptions(tag="v1.2.3", non_interactive=True))

    def test_user_cancels_rollback(self, mock_pyproject, monkeypatch):
        """Should exit when user cancels rollback confirmation."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "tag" in cmd and "--sort" in cmd:
                result.stdout = "v1.2.3\nv1.2.2\n"
            elif "show" in cmd:
                result.stdout = "abc123|2025-01-01|Some commit"
            elif "log" in cmd:
                result.stdout = "Some commit"
            return result

        class MockConfirmFalse:
            def ask(self):
                return False

        monkeypatch.setattr(rollback_mod.qs, "confirm", lambda *a, **kw: MockConfirmFalse())

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(True, True)),
            pytest.raises(typer.Exit) as exc_info,
        ):
            rollback_command(RollbackOptions(tag="v1.2.3"))
        assert exc_info.value.exit_code == 0

    def test_remote_tag_delete_failure_aborts(self, mock_pyproject):
        """Should abort if remote tag deletion fails."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "tag" in cmd and "--sort" in cmd:
                result.stdout = "v1.2.3\nv1.2.2\n"
            elif "show" in cmd:
                result.stdout = "abc123|2025-01-01|Some commit"
            elif "log" in cmd:
                result.stdout = "Some commit"
            elif "push" in cmd and ":refs/tags" in str(cmd):
                result.returncode = 1
                result.stderr = "error: unable to delete"
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(True, True)),
            pytest.raises(typer.Exit) as exc_info,
        ):
            rollback_command(RollbackOptions(tag="v1.2.3", non_interactive=True))
        assert exc_info.value.exit_code == 1

    def test_adds_v_prefix_to_tag(self, mock_pyproject):
        """Should automatically add 'v' prefix if missing."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "tag" in cmd and "--sort" in cmd:
                result.stdout = "v1.2.3\nv1.2.2\n"
            elif "show" in cmd:
                result.stdout = "abc123|2025-01-01|Some commit"
            elif "log" in cmd:
                result.stdout = "Some commit"
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(True, False)) as mock_check,
        ):
            rollback_command(RollbackOptions(tag="1.2.3", dry_run=True, non_interactive=True))
            # Should have been called with "v1.2.3"
            mock_check.assert_called_with("v1.2.3")

    def test_local_only_tag_rollback(self, mock_pyproject):
        """Should rollback a tag that only exists locally."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "tag" in cmd and "--sort" in cmd:
                result.stdout = "v1.2.3\nv1.2.2\n"
            elif "show" in cmd:
                result.stdout = "abc123|2025-01-01|Some commit"
            elif "log" in cmd:
                result.stdout = "Some commit"
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(True, False)),
        ):
            rollback_command(RollbackOptions(tag="v1.2.3", non_interactive=True))

    def test_non_interactive_no_tag_uses_most_recent(self, mock_pyproject):
        """Should use most recent tag in non-interactive mode without explicit tag."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif ("tag" in cmd and "-l" in cmd) or ("tag" in cmd and "--sort" in cmd):
                result.stdout = "v1.2.3\nv1.2.2\n"
            elif "show" in cmd:
                result.stdout = "abc123|2025-01-01|Some commit"
            elif "log" in cmd:
                result.stdout = "Some commit"
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(True, False)),
        ):
            rollback_command(RollbackOptions(non_interactive=True))

    def test_non_interactive_no_tag_and_no_tags_exits(self, mock_pyproject):
        """Should exit when no tags found in non-interactive mode without explicit tag."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "tag" in cmd:
                result.stdout = ""
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            pytest.raises(typer.Exit) as exc_info,
        ):
            rollback_command(RollbackOptions(non_interactive=True))
        assert exc_info.value.exit_code == 1

    def test_rollback_with_revert_and_push(self, mock_pyproject):
        """Should revert bump and push in non-interactive mode."""

        def mock_run_git(cmd, check=True):
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            if "rev-parse" in cmd and "--abbrev-ref" in cmd:
                result.stdout = "main"
            elif "tag" in cmd and "--sort" in cmd:
                result.stdout = "v1.2.3\nv1.2.2\n"
            elif "show" in cmd:
                result.stdout = "abc123|2025-01-01|Bump version: 1.2.2 → 1.2.3"
            elif "log" in cmd and "-1" in cmd:
                result.stdout = "Bump version: 1.2.2 → 1.2.3"
            elif "rev-list" in cmd:
                result.stdout = "abc123def456"
            elif "revert" in cmd or "push" in cmd:
                result.returncode = 0
            return result

        with (
            patch.object(rollback_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_git_mod, "run_git_command", side_effect=mock_run_git),
            patch.object(rollback_mod, "check_tag_exists", return_value=(True, True)),
        ):
            rollback_command(RollbackOptions(tag="v1.2.3", revert_bump=True, non_interactive=True))


# ──────────────────────────────────────────────
# CLI integration tests
# ──────────────────────────────────────────────


class TestRollbackCLI:
    """Tests for the rollback CLI command integration."""

    def test_cli_rollback_dry_run(self, monkeypatch):
        """Test the rollback CLI command with --dry-run."""
        from typer.testing import CliRunner

        import rhiza_tools.cli as cli_mod

        mock_rollback = MagicMock()
        monkeypatch.setattr(cli_mod, "rollback_command", mock_rollback)

        runner = CliRunner()
        result = runner.invoke(cli_mod.app, ["rollback", "v1.2.3", "--dry-run"])
        assert result.exit_code == 0

        mock_rollback.assert_called_once()
        options = mock_rollback.call_args[0][0]
        assert isinstance(options, RollbackOptions)
        assert options.tag == "v1.2.3"
        assert options.dry_run is True
        assert options.revert_bump is False
        assert options.non_interactive is False

    def test_cli_rollback_with_revert_bump(self, monkeypatch):
        """Test the rollback CLI command with --revert-bump."""
        from typer.testing import CliRunner

        import rhiza_tools.cli as cli_mod

        mock_rollback = MagicMock()
        monkeypatch.setattr(cli_mod, "rollback_command", mock_rollback)

        runner = CliRunner()
        result = runner.invoke(cli_mod.app, ["rollback", "v1.2.3", "--revert-bump", "-y"])
        assert result.exit_code == 0

        options = mock_rollback.call_args[0][0]
        assert options.tag == "v1.2.3"
        assert options.revert_bump is True
        assert options.non_interactive is True

    def test_cli_rollback_no_tag(self, monkeypatch):
        """Test the rollback CLI command without a tag argument."""
        from typer.testing import CliRunner

        import rhiza_tools.cli as cli_mod

        mock_rollback = MagicMock()
        monkeypatch.setattr(cli_mod, "rollback_command", mock_rollback)

        runner = CliRunner()
        result = runner.invoke(cli_mod.app, ["rollback", "--dry-run"])
        assert result.exit_code == 0

        options = mock_rollback.call_args[0][0]
        assert options.tag is None
        assert options.dry_run is True


# ---------------------------------------------------------------------------
# Branch/edge-case coverage relocated from the former test_coverage_100.py
# ---------------------------------------------------------------------------


class TestPushRevertEOF:
    """Tests for EOFError handling in rollback._push_revert."""

    def test_eof_in_confirm_proceeds_with_push(self):
        """rollback.py:325-327 – EOFError during confirm causes push to proceed."""
        import rhiza_tools.commands.rollback as rollback_mod
        from rhiza_tools.commands.rollback import _push_revert

        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = EOFError

        mock_git = MagicMock()
        mock_git.returncode = 0

        with (
            patch("questionary.confirm", return_value=mock_confirm),
            patch.object(rollback_mod, "run_git_command", return_value=mock_git),
        ):
            result = _push_revert(dry_run=False, non_interactive=False)

        assert result is True


class TestResolveTag:
    """Tests for tag resolution paths in rollback._resolve_tag."""

    def test_non_interactive_with_recent_tag(self):
        """rollback.py:463-469 – non_interactive mode picks most recent tag."""
        import rhiza_tools.commands.rollback as rollback_mod
        from rhiza_tools.commands.rollback import RollbackOptions, _resolve_tag

        with patch.object(rollback_mod, "_get_recent_tags", return_value=["v1.2.3"]):
            result = _resolve_tag(RollbackOptions(tag=None, non_interactive=True))

        assert result == "v1.2.3"

    def test_non_interactive_no_tags_exits(self):
        """rollback.py:465-467 – non_interactive with no tags raises Exit."""
        import rhiza_tools.commands.rollback as rollback_mod
        from rhiza_tools.commands.rollback import RollbackOptions, _resolve_tag

        with patch.object(rollback_mod, "_get_recent_tags", return_value=[]), pytest.raises(typer.Exit):
            _resolve_tag(RollbackOptions(tag=None, non_interactive=True))

    def test_interactive_selection(self):
        """rollback.py:471-472 – interactive mode calls _select_tag_interactively."""
        import rhiza_tools.commands.rollback as rollback_mod
        from rhiza_tools.commands.rollback import RollbackOptions, _resolve_tag

        with (
            patch.object(rollback_mod, "_get_recent_tags", return_value=["v1.2.3", "v1.2.2"]),
            patch.object(rollback_mod, "_select_tag_interactively", return_value="v1.2.3"),
        ):
            result = _resolve_tag(RollbackOptions(tag=None, non_interactive=False))

        assert result == "v1.2.3"


class TestShouldRevertBump:
    """Tests for interactive confirm paths in rollback._should_revert_bump."""

    def test_interactive_user_confirms_revert(self):
        """rollback.py:500-507 – interactive confirm returns True."""
        from rhiza_tools.commands.rollback import RollbackOptions, _should_revert_bump

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True

        with patch("questionary.confirm", return_value=mock_confirm):
            result = _should_revert_bump(
                options=RollbackOptions(revert_bump=False, non_interactive=False, dry_run=False),
                exists_locally=True,
                is_bump=True,
            )

        assert result is True

    def test_interactive_eof_returns_false(self):
        """rollback.py:508-510 – EOFError during confirm returns False."""
        from rhiza_tools.commands.rollback import RollbackOptions, _should_revert_bump

        mock_confirm = MagicMock()
        mock_confirm.ask.side_effect = EOFError

        with patch("questionary.confirm", return_value=mock_confirm):
            result = _should_revert_bump(
                options=RollbackOptions(revert_bump=False, non_interactive=False, dry_run=False),
                exists_locally=True,
                is_bump=True,
            )

        assert result is False


class TestExecuteRollback:
    """Tests for edge-case branches in rollback._execute_rollback."""

    def test_tag_commit_not_found_skips_revert(self):
        """rollback.py:546-548 – missing tag commit skips revert but continues."""
        import rhiza_tools.commands.rollback as rollback_mod
        from rhiza_tools.commands.rollback import _execute_rollback

        with (
            patch.object(rollback_mod, "_get_tag_commit", return_value=None),
            patch.object(rollback_mod, "_delete_remote_tag", return_value=True),
            patch.object(rollback_mod, "_delete_local_tag", return_value=True),
        ):
            result = _execute_rollback(
                tag="v1.0.0",
                exists_locally=True,
                exists_remotely=True,
                revert_bump=True,
                is_bump=True,
                dry_run=False,
                non_interactive=True,
            )

        assert result is True

    def test_delete_local_tag_fails_not_dry_run(self):
        """rollback.py:561-563 – warning shown when local tag deletion fails."""
        import rhiza_tools.commands.rollback as rollback_mod
        from rhiza_tools.commands.rollback import _execute_rollback

        with (
            patch.object(rollback_mod, "_delete_remote_tag", return_value=True),
            patch.object(rollback_mod, "_delete_local_tag", return_value=False),
        ):
            result = _execute_rollback(
                tag="v1.0.0",
                exists_locally=True,
                exists_remotely=True,
                revert_bump=False,
                is_bump=False,
                dry_run=False,
                non_interactive=True,
            )

        assert result is False

    def test_revert_bump_fails_not_dry_run(self):
        """rollback.py:568-571 – warning shown when bump revert fails."""
        import rhiza_tools.commands.rollback as rollback_mod
        from rhiza_tools.commands.rollback import _execute_rollback

        with (
            patch.object(rollback_mod, "_get_tag_commit", return_value="abc1234"),
            patch.object(rollback_mod, "_delete_remote_tag", return_value=True),
            patch.object(rollback_mod, "_delete_local_tag", return_value=True),
            patch.object(rollback_mod, "_revert_bump_commit", return_value=False),
        ):
            result = _execute_rollback(
                tag="v1.0.0",
                exists_locally=True,
                exists_remotely=True,
                revert_bump=True,
                is_bump=True,
                dry_run=False,
                non_interactive=True,
            )

        assert result is False

    def test_push_revert_fails(self):
        """rollback.py:573-574 – success=False when push revert fails."""
        import rhiza_tools.commands.rollback as rollback_mod
        from rhiza_tools.commands.rollback import _execute_rollback

        with (
            patch.object(rollback_mod, "_get_tag_commit", return_value="abc1234"),
            patch.object(rollback_mod, "_delete_remote_tag", return_value=True),
            patch.object(rollback_mod, "_delete_local_tag", return_value=True),
            patch.object(rollback_mod, "_revert_bump_commit", return_value=True),
            patch.object(rollback_mod, "_push_revert", return_value=False),
        ):
            result = _execute_rollback(
                tag="v1.0.0",
                exists_locally=True,
                exists_remotely=True,
                revert_bump=True,
                is_bump=True,
                dry_run=False,
                non_interactive=True,
            )

        assert result is False


class TestPrintRollbackSummary:
    """Tests for both branches in rollback._print_rollback_summary."""

    def test_success_with_previous_tag(self):
        """rollback.py:595-598 – previous version displayed on success."""
        from rhiza_tools.commands.rollback import _print_rollback_summary

        _print_rollback_summary(dry_run=False, success=True, previous_tag="v1.0.0")

    def test_failure_prints_warning(self):
        """rollback.py:592-593 – warning printed when success=False."""
        from rhiza_tools.commands.rollback import _print_rollback_summary

        _print_rollback_summary(dry_run=False, success=False, previous_tag=None)
