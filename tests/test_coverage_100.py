"""Tests to achieve 100% coverage across all modules."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from rhiza_tools.cli import app

runner = CliRunner()


# ─── console.py ──────────────────────────────────────────────────────────────


class TestConsole:
    """Tests for console.py verbose configuration path."""

    def test_configure_verbose_adds_logger_handler(self):
        """console.py:46 – logger.add is called when verbose=True."""
        from rhiza_tools import console

        console.configure(verbose=True)
        assert console.is_verbose() is True
        # Cleanup to avoid polluting other tests
        console.configure(verbose=False)


# ─── cli.py ──────────────────────────────────────────────────────────────────


class TestCLI:
    """Tests for uncovered branches in cli.py."""

    def test_apply_verbose_true(self):
        """cli.py:62 – configure_console called with verbose=True."""
        from rhiza_tools.cli import _apply_verbose

        with patch("rhiza_tools.cli.configure_console") as mock_configure:
            _apply_verbose(True)
            mock_configure.assert_called_once_with(verbose=True)

    def test_bump_invalid_language(self):
        """cli.py:146-151 – invalid language exits with code 1."""
        result = runner.invoke(app, ["bump", "--language", "ruby"])
        assert result.exit_code == 1

    def test_release_invalid_language(self):
        """cli.py:272-276 – invalid language in release exits with code 1."""
        result = runner.invoke(app, ["release", "--language", "ruby"])
        assert result.exit_code == 1

    def test_analyze_benchmarks_cli(self, monkeypatch):
        """cli.py:459-460 – analyze-benchmarks command invokes analyze_benchmarks_command."""
        mock_cmd = MagicMock()
        monkeypatch.setattr("rhiza_tools.cli.analyze_benchmarks_command", mock_cmd)
        result = runner.invoke(app, ["analyze-benchmarks"])
        assert result.exit_code == 0
        mock_cmd.assert_called_once()

    def test_analyze_benchmarks_cli_verbose(self, monkeypatch):
        """cli.py:459 – _apply_verbose is triggered for analyze-benchmarks --verbose."""
        mock_cmd = MagicMock()
        monkeypatch.setattr("rhiza_tools.cli.analyze_benchmarks_command", mock_cmd)
        result = runner.invoke(app, ["analyze-benchmarks", "--verbose"])
        assert result.exit_code == 0


# ─── _shared.py ──────────────────────────────────────────────────────────────


class TestShared:
    """Tests for uncovered branches in commands/_shared.py."""

    def test_get_current_version_success(self, tmp_path, monkeypatch):
        """_shared.py:81-82 – returns version string from valid pyproject.toml."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\nversion = '1.2.3'\n")
        from rhiza_tools.commands._shared import get_current_version

        assert get_current_version() == "1.2.3"

    def test_get_current_version_exception(self, tmp_path, monkeypatch):
        """_shared.py:83-85 – exits when pyproject.toml cannot be parsed."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("[invalid toml [[[")
        from rhiza_tools.commands._shared import get_current_version

        with pytest.raises(typer.Exit):
            get_current_version()


# ─── bump.py ─────────────────────────────────────────────────────────────────


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
            patch("rhiza_tools.commands.bump.do_bump", side_effect=Exception("bump failed")),
            pytest.raises(typer.Exit),
        ):
            _execute_bump("1.0.1", mock_config, mock_config_path, dry_run=False)

    def test_do_bump_exception_dry_run(self):
        """bump.py:636-637,644 – Exit raised in dry_run mode when do_bump fails."""
        from rhiza_tools.commands.bump import _execute_bump

        mock_config = MagicMock()
        mock_config_path = MagicMock()

        with (
            patch("rhiza_tools.commands.bump.do_bump", side_effect=Exception("bump failed")),
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


# ─── release.py ──────────────────────────────────────────────────────────────


class TestResolveInteractivePromptBumpExit:
    """Tests for exception paths in release._resolve_interactive_prompt."""

    def test_get_interactive_bump_raises_exit(self):
        """release.py:338-339 – returns (False, None) when get_interactive_bump_type raises Exit."""
        from rhiza_tools.commands.bump import Language
        from rhiza_tools.commands.release import _resolve_interactive_prompt

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True

        with (
            patch("questionary.confirm", return_value=mock_confirm),
            patch("rhiza_tools.commands.release.get_current_version", return_value="1.0.0"),
            patch(
                "rhiza_tools.commands.release.get_interactive_bump_type",
                side_effect=typer.Exit(),
            ),
        ):
            result = _resolve_interactive_prompt(Language.PYTHON)

        assert result == (False, None)

    def test_get_interactive_bump_raises_eof(self):
        """release.py:338-339 – returns (False, None) when get_interactive_bump_type raises EOFError."""
        from rhiza_tools.commands.bump import Language
        from rhiza_tools.commands.release import _resolve_interactive_prompt

        mock_confirm = MagicMock()
        mock_confirm.ask.return_value = True

        with (
            patch("questionary.confirm", return_value=mock_confirm),
            patch("rhiza_tools.commands.release.get_current_version", return_value="1.0.0"),
            patch(
                "rhiza_tools.commands.release.get_interactive_bump_type",
                side_effect=EOFError,
            ),
        ):
            result = _resolve_interactive_prompt(Language.PYTHON)

        assert result == (False, None)


class TestValidateTagState:
    """Tests for tag detail display path in release._validate_tag_state."""

    def test_shows_tag_details_when_git_show_succeeds(self):
        """release.py:408-413 – tag details are displayed when git show succeeds."""
        import rhiza_tools.commands.release as release_mod
        from rhiza_tools.commands.release import _validate_tag_state

        mock_exists = MagicMock(return_value=(True, False))
        mock_git = MagicMock()
        mock_git.returncode = 0
        mock_git.stdout = "abc1234567890|2024-01-01 12:00:00|Bump version to 1.0.1\n"

        with (
            patch.object(release_mod, "check_tag_exists", mock_exists),
            patch.object(release_mod, "run_git_command", return_value=mock_git),
        ):
            _validate_tag_state("v1.0.1", "1.0.1")  # should not raise


class TestShowCommitsSinceLastTag:
    """Tests for commit display in release._show_commits_since_last_tag."""

    def test_shows_commits_with_previous_tag(self):
        """release.py:430-443 – commits since last tag are displayed."""
        import rhiza_tools.commands.release as release_mod
        from rhiza_tools.commands.release import _show_commits_since_last_tag

        tags_result = MagicMock()
        tags_result.returncode = 0
        tags_result.stdout = "v1.0.1\nv1.0.0\n"

        commits_result = MagicMock()
        commits_result.returncode = 0
        commits_result.stdout = "abc1234 feat: add feature\ndef5678 fix: fix bug\n"

        with patch.object(release_mod, "run_git_command", side_effect=[tags_result, commits_result]):
            _show_commits_since_last_tag("v1.0.1")  # should not raise

    def test_shows_more_than_10_commits(self):
        """release.py:442-443 – truncation message shown when >10 commits."""
        import rhiza_tools.commands.release as release_mod
        from rhiza_tools.commands.release import _show_commits_since_last_tag

        tags_result = MagicMock()
        tags_result.returncode = 0
        tags_result.stdout = "v1.0.1\nv1.0.0\n"

        many_commits = "\n".join(f"abc{i:04d} commit {i}" for i in range(12))
        commits_result = MagicMock()
        commits_result.returncode = 0
        commits_result.stdout = many_commits

        with patch.object(release_mod, "run_git_command", side_effect=[tags_result, commits_result]):
            _show_commits_since_last_tag("v1.0.1")


class TestHandleTagValidation:
    """Tests for dry-run tag validation in release._handle_tag_validation."""

    def test_dry_run_with_bump_tag_already_on_remote(self):
        """release.py:543-547 – dry_run with bump raises Exit when tag already on remote."""
        import rhiza_tools.commands.release as release_mod
        from rhiza_tools.commands.release import _handle_tag_validation

        with (
            patch.object(release_mod, "check_tag_exists", return_value=(False, True)),
            pytest.raises(typer.Exit),
        ):
            _handle_tag_validation(
                dry_run=True,
                bumped_new_version="1.0.1",
                tag="v1.0.1",
                current_version="1.0.0",
            )


# ─── rollback.py ─────────────────────────────────────────────────────────────


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
