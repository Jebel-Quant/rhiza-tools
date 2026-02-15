"""End-to-end tests for bump and release command user flows.

These tests exercise the full command workflows as described in the TESTING_GUIDE.md,
covering interactive and non-interactive modes, dry-run, push, branch operations,
and the --with-bump release flag.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
import typer

from rhiza_tools.commands.bump import (
    BumpOptions,
    Language,
    bump_command,
    get_current_version,
)
from rhiza_tools.commands.release import (
    _get_bump_type_interactively,
    release_command,
)

GIT = subprocess.run(["which", "git"], capture_output=True, text=True, check=True).stdout.strip()


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture
def e2e_project(tmp_path, monkeypatch):
    """Create a fully-initialized project with git repo and bumpversion config.

    This fixture provides a realistic project environment with:
    - Git repo with initial commit
    - pyproject.toml at version 0.1.0
    - .rhiza/.cfg.toml with bumpversion config
    - Clean working tree
    """
    monkeypatch.chdir(tmp_path)

    # Prevent git from walking up to the real repo
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))

    # Initialize git repo
    subprocess.run([GIT, "init"], check=True, capture_output=True)
    subprocess.run([GIT, "config", "user.email", "test@example.com"], check=True, capture_output=True)
    subprocess.run([GIT, "config", "user.name", "Test User"], check=True, capture_output=True)

    # Create pyproject.toml
    pyproject_content = """[project]
name = "test-project"
version = "0.1.0"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    # Create bumpversion config
    rhiza_dir = tmp_path / ".rhiza"
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
tag = true
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
    (rhiza_dir / ".cfg.toml").write_text(config_content)

    # Initial commit
    subprocess.run([GIT, "add", "."], check=True, capture_output=True)
    subprocess.run([GIT, "commit", "-m", "Initial commit"], check=True, capture_output=True)

    return tmp_path


# ──────────────────────────────────────────────
# Test 1: Interactive Bump (Default Behavior)
# ──────────────────────────────────────────────


class TestInteractiveBump:
    """Test 1: Interactive bump with mock prompts."""

    def test_interactive_bump_selects_patch(self, e2e_project, monkeypatch):
        """User selects Patch from interactive menu."""

        class MockSelect:
            def ask(self):
                return "Patch (0.1.0 -> 0.1.1)"

        confirm_calls = []

        class MockConfirm:
            def ask(self):
                confirm_calls.append(True)
                # First call: "Proceed with bump?" -> Yes
                # Second call: "Push to remote?" -> No
                return len(confirm_calls) == 1

        select_calls = []

        def mock_select(*args, **kwargs):
            select_calls.append(args)
            return MockSelect()

        def mock_confirm(*args, **kwargs):
            return MockConfirm()

        monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", mock_select)
        monkeypatch.setattr("rhiza_tools.commands.bump.qs.confirm", mock_confirm)

        bump_command(BumpOptions(version=None))

        assert get_current_version(Language.PYTHON) == "0.1.1"

    def test_interactive_bump_selects_minor(self, e2e_project, monkeypatch):
        """User selects Minor from interactive menu."""

        class MockSelect:
            def ask(self):
                return "Minor (0.1.0 -> 0.2.0)"

        confirm_calls = []

        class MockConfirm:
            def ask(self):
                confirm_calls.append(True)
                return len(confirm_calls) == 1

        monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", lambda *a, **kw: MockSelect())
        monkeypatch.setattr("rhiza_tools.commands.bump.qs.confirm", lambda *a, **kw: MockConfirm())

        bump_command(BumpOptions(version=None))

        assert get_current_version(Language.PYTHON) == "0.2.0"

    def test_interactive_bump_selects_major(self, e2e_project, monkeypatch):
        """User selects Major from interactive menu."""

        class MockSelect:
            def ask(self):
                return "Major (0.1.0 -> 1.0.0)"

        confirm_calls = []

        class MockConfirm:
            def ask(self):
                confirm_calls.append(True)
                return len(confirm_calls) == 1

        monkeypatch.setattr("rhiza_tools.commands.bump.qs.select", lambda *a, **kw: MockSelect())
        monkeypatch.setattr("rhiza_tools.commands.bump.qs.confirm", lambda *a, **kw: MockConfirm())

        bump_command(BumpOptions(version=None))

        assert get_current_version(Language.PYTHON) == "1.0.0"


# ──────────────────────────────────────────────
# Test 2: Interactive Bump with Push
# ──────────────────────────────────────────────


class TestInteractiveBumpWithPush:
    """Test 2: Interactive bump with --push flag."""

    def test_bump_with_push_calls_push_handler(self, e2e_project, monkeypatch):
        """Bump with --push flag triggers push to remote."""
        push_called = {"called": False}

        def mock_push(*args, **kwargs):
            push_called["called"] = True

        with patch("rhiza_tools.commands.bump._handle_push_to_remote", mock_push):
            bump_command(BumpOptions(version="patch", push=True))

        assert get_current_version(Language.PYTHON) == "0.1.1"
        assert push_called["called"]

    def test_bump_push_implies_commit(self, e2e_project, monkeypatch):
        """Push flag implies commit flag."""
        push_called = {"called": False}

        def mock_push(*args, **kwargs):
            push_called["called"] = True

        with patch("rhiza_tools.commands.bump._handle_push_to_remote", mock_push):
            bump_command(BumpOptions(version="patch", push=True, commit=False))

        assert get_current_version(Language.PYTHON) == "0.1.1"
        assert push_called["called"]


# ──────────────────────────────────────────────
# Test 3: Non-Interactive Bump with Dry-Run
# ──────────────────────────────────────────────


class TestNonInteractiveBumpDryRun:
    """Test 3: Non-interactive bump with --dry-run."""

    def test_dry_run_does_not_change_version(self, e2e_project):
        """Dry-run should not actually change the version."""
        original_version = get_current_version(Language.PYTHON)

        bump_command(BumpOptions(version="minor", dry_run=True))

        assert get_current_version(Language.PYTHON) == original_version

    def test_dry_run_patch(self, e2e_project):
        """Dry-run patch should not change version."""
        bump_command(BumpOptions(version="patch", dry_run=True))
        assert get_current_version(Language.PYTHON) == "0.1.0"

    def test_dry_run_major(self, e2e_project):
        """Dry-run major should not change version."""
        bump_command(BumpOptions(version="major", dry_run=True))
        assert get_current_version(Language.PYTHON) == "0.1.0"

    def test_dry_run_leaves_git_clean(self, e2e_project):
        """Dry-run should not leave any git changes."""
        bump_command(BumpOptions(version="minor", dry_run=True))

        result = subprocess.run([GIT, "status", "--porcelain"], capture_output=True, text=True, check=True)
        assert result.stdout.strip() == ""


# ──────────────────────────────────────────────
# Test 4: Non-Interactive Bump with Commit and Push
# ──────────────────────────────────────────────


class TestNonInteractiveBumpCommitPush:
    """Test 4: Non-interactive bump with --commit and --push."""

    def test_bump_with_commit_creates_git_commit(self, e2e_project):
        """Bump with --commit should create a git commit."""
        bump_command(BumpOptions(version="patch", commit=True))

        assert get_current_version(Language.PYTHON) == "0.1.1"

        # Verify a commit was made with the version tag
        result = subprocess.run(
            [GIT, "log", "--oneline", "-1"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "0.1.1" in result.stdout or "Bump" in result.stdout

    def test_bump_commit_push_full_flow(self, e2e_project):
        """Full non-interactive flow: bump, commit, push."""
        push_called = {"called": False}

        def mock_push(*args, **kwargs):
            push_called["called"] = True

        with patch("rhiza_tools.commands.bump._handle_push_to_remote", mock_push):
            bump_command(BumpOptions(version="patch", commit=True, push=True))

        assert get_current_version(Language.PYTHON) == "0.1.1"
        assert push_called["called"]


# ──────────────────────────────────────────────
# Test 5: Bump on Specific Branch
# ──────────────────────────────────────────────


class TestBumpOnBranch:
    """Test 5: Bump on a specific branch."""

    def test_bump_on_branch_and_restore(self, e2e_project):
        """Bump on feature branch should restore original branch."""
        # Create a feature branch
        subprocess.run([GIT, "checkout", "-b", "feature-branch"], check=True, capture_output=True)
        subprocess.run([GIT, "checkout", "-"], check=True, capture_output=True)

        original_branch = subprocess.run(
            [GIT, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        # Bump on feature branch
        bump_command(BumpOptions(version="patch", branch="feature-branch"))

        # Should be back on original branch
        current = subprocess.run(
            [GIT, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert current == original_branch

    def test_bump_on_branch_dry_run(self, e2e_project):
        """Dry-run bump on branch should not change anything."""
        subprocess.run([GIT, "checkout", "-b", "feature-branch"], check=True, capture_output=True)
        subprocess.run([GIT, "checkout", "-"], check=True, capture_output=True)

        bump_command(BumpOptions(version="patch", branch="feature-branch", dry_run=True))

        # Version on any branch should still be 0.1.0
        assert get_current_version(Language.PYTHON) == "0.1.0"


# ──────────────────────────────────────────────
# Test 6: Bump Dry-Run Preview
# ──────────────────────────────────────────────


class TestBumpDryRunPreview:
    """Test 6: Bump dry-run shows preview but makes no changes."""

    def test_major_dry_run_no_changes(self, e2e_project):
        """Major dry-run should show preview but not change files."""
        bump_command(BumpOptions(version="major", dry_run=True))

        assert get_current_version(Language.PYTHON) == "0.1.0"

        # Verify no changes in git
        result = subprocess.run([GIT, "diff", "pyproject.toml"], capture_output=True, text=True, check=True)
        assert result.stdout.strip() == ""


# ──────────────────────────────────────────────
# Test 7: Interactive Release (Default Behavior)
# ──────────────────────────────────────────────


def _make_mock_git_for_release(
    current_branch: str = "main",
    default_branch: str = "main",
    tag_exists_locally: bool = True,
    tag_exists_remotely: bool = False,
    version: str = "0.1.0",
):
    """Build a mock for run_git_command suitable for release tests."""

    def mock_run_git_command(cmd, check=True):
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""

        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = current_branch
        elif "symbolic-full-name" in cmd:
            result.stdout = f"origin/{current_branch}"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = f"* remote origin\n  HEAD branch: {default_branch}\n"
        elif "rev-parse" in cmd and any(f"v{version}" in arg for arg in cmd):
            result.returncode = 0 if tag_exists_locally else 1
            result.stdout = "abc123" if tag_exists_locally else ""
        elif "rev-parse" in cmd:
            result.stdout = "abc123"
        elif "merge-base" in cmd:
            result.stdout = "abc123"
        elif "ls-remote" in cmd and "--tags" in cmd:
            result.returncode = 0 if tag_exists_remotely else 1
        elif "tag" in cmd and "--sort" in cmd:
            result.stdout = f"v{version}\nv0.0.1"
        elif "log" in cmd:
            result.stdout = "abc1234 Some commit\ndef5678 Another commit"
        elif "remote" in cmd and "get-url" in cmd:
            result.stdout = "https://github.com/user/repo.git"
        elif "show" in cmd and "--format" in cmd:
            result.stdout = "abc123|2026-01-15|Bump version"
        elif "status" in cmd and "--porcelain" in cmd:
            result.stdout = ""
        elif "fetch" in cmd:
            pass

        return result

    return mock_run_git_command


class TestInteractiveRelease:
    """Test 7: Interactive release (default behavior)."""

    def test_release_dry_run_shows_info(self, e2e_project):
        """Dry-run release should show version and tag info without changes."""
        # Create a tag for the current version
        subprocess.run([GIT, "tag", "v0.1.0"], check=True, capture_output=True)

        mock_git = _make_mock_git_for_release(tag_exists_locally=True)

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.typer.confirm", return_value=True):
                release_command(dry_run=True)

        # Version should be unchanged
        assert get_current_version(Language.PYTHON) == "0.1.0"

    def test_release_user_declines_push(self, e2e_project):
        """User declines push in interactive mode."""
        subprocess.run([GIT, "tag", "v0.1.0"], check=True, capture_output=True)

        mock_git = _make_mock_git_for_release(tag_exists_locally=True)

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    release_command()
                assert exc_info.value.exit_code == 0


# ──────────────────────────────────────────────
# Test 8: Interactive Release with Bump
# ──────────────────────────────────────────────


class TestInteractiveReleaseWithBump:
    """Test 8: Interactive release with version bump."""

    def test_release_with_bump_flag_dry_run(self, e2e_project):
        """Release --bump MINOR --dry-run should show bumped version tag."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="0.2.0",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command") as mock_bump:
                release_command(bump_type="MINOR", push=True, dry_run=True)

        # bump_command should be called with BumpOptions containing the explicit version
        mock_bump.assert_called_once()
        call_args = mock_bump.call_args[0]
        assert len(call_args) == 1
        options = call_args[0]
        assert isinstance(options, BumpOptions)
        assert options.version == "0.2.0"

        # Version should be unchanged (dry-run)
        assert get_current_version(Language.PYTHON) == "0.1.0"


# ──────────────────────────────────────────────
# Test 9: Non-Interactive Release with Dry-Run
# ──────────────────────────────────────────────


class TestNonInteractiveReleaseDryRun:
    """Test 9: Non-interactive release dry-run."""

    def test_release_dry_run_no_changes(self, e2e_project):
        """Dry-run release should make no changes."""
        subprocess.run([GIT, "tag", "v0.1.0"], check=True, capture_output=True)

        mock_git = _make_mock_git_for_release(tag_exists_locally=True)

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            release_command(dry_run=True, non_interactive=True)

        assert get_current_version(Language.PYTHON) == "0.1.0"

        # Git should be clean
        result = subprocess.run([GIT, "status", "--porcelain"], capture_output=True, text=True, check=True)
        assert result.stdout.strip() == ""


# ──────────────────────────────────────────────
# Test 10: Non-Interactive Release with Bump and Push
# ──────────────────────────────────────────────


class TestNonInteractiveReleaseBumpPush:
    """Test 10: Non-interactive release with --bump and --push."""

    def test_release_bump_push_dry_run(self, e2e_project):
        """--bump MINOR --push --dry-run: should simulate full flow."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="0.2.0",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command") as mock_bump:
                release_command(bump_type="MINOR", push=True, dry_run=True)

        mock_bump.assert_called_once()

    def test_release_bump_patch_push_dry_run(self, e2e_project):
        """--bump PATCH --push --dry-run: simulate patch release."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="0.1.1",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command") as mock_bump:
                release_command(bump_type="PATCH", push=True, dry_run=True)

        mock_bump.assert_called_once()

    def test_release_bump_major_push_dry_run(self, e2e_project):
        """--bump MAJOR --push --dry-run: simulate major release."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="1.0.0",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command") as mock_bump:
                release_command(bump_type="MAJOR", push=True, dry_run=True)

        mock_bump.assert_called_once()


# ──────────────────────────────────────────────
# Test 11: Release Without Bump (Just Push Tag)
# ──────────────────────────────────────────────


class TestReleaseWithoutBump:
    """Test 11: Release without bump - just push existing tag."""

    def test_release_push_existing_tag_dry_run(self, e2e_project):
        """Push existing tag in dry-run mode."""
        subprocess.run([GIT, "tag", "v0.1.0"], check=True, capture_output=True)

        mock_git = _make_mock_git_for_release(tag_exists_locally=True)

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            release_command(push=True, dry_run=True)

        assert get_current_version(Language.PYTHON) == "0.1.0"

    def test_release_push_non_interactive(self, e2e_project):
        """Non-interactive push of existing tag."""
        subprocess.run([GIT, "tag", "v0.1.0"], check=True, capture_output=True)

        mock_git = _make_mock_git_for_release(tag_exists_locally=True)

        push_called = {"called": False}

        def mock_push_tag(tag, dry_run=False, non_interactive=False):
            push_called["called"] = True

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.push_tag", side_effect=mock_push_tag):
                release_command(push=True, non_interactive=True)

        assert push_called["called"]


# ──────────────────────────────────────────────
# Test 12: Release with Commit Listing
# ──────────────────────────────────────────────


class TestReleaseCommitListing:
    """Test 12: Release shows commits since last tag."""

    def test_release_shows_commits(self, e2e_project):
        """Release dry-run should complete without error showing commits."""
        subprocess.run([GIT, "tag", "v0.1.0"], check=True, capture_output=True)

        mock_git = _make_mock_git_for_release(tag_exists_locally=True)

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.typer.confirm", return_value=True):
                # Should complete without errors
                release_command(dry_run=True)


# ──────────────────────────────────────────────
# Test 13: Bump with Dirty Working Directory
# ──────────────────────────────────────────────


class TestBumpDirtyWorkingDirectory:
    """Test 13: Bump behavior with dirty working directory."""

    def test_bump_dirty_with_allow_dirty_succeeds(self, e2e_project):
        """Bump with --allow-dirty should succeed even with uncommitted changes."""
        (e2e_project / "dirty.txt").write_text("dirty")
        subprocess.run([GIT, "add", "dirty.txt"], check=True, capture_output=True)

        bump_command(BumpOptions(version="patch", allow_dirty=True))
        assert get_current_version(Language.PYTHON) == "0.1.1"

    def test_bump_dirty_without_commit_succeeds(self, e2e_project):
        """Bump without commit should succeed (bumps file only)."""
        (e2e_project / "dirty.txt").write_text("dirty")
        subprocess.run([GIT, "add", "dirty.txt"], check=True, capture_output=True)

        # Without commit flag, bumpversion may still allow dirty (depends on config)
        bump_command(BumpOptions(version="patch"))
        assert get_current_version(Language.PYTHON) == "0.1.1"


# ──────────────────────────────────────────────
# Test 14: Release with Missing Tag
# ──────────────────────────────────────────────


class TestReleaseMissingTag:
    """Test 14: Release fails when tag doesn't exist locally."""

    def test_release_missing_tag_fails(self, e2e_project):
        """Release should fail if tag doesn't exist locally."""
        mock_git = _make_mock_git_for_release(tag_exists_locally=False)

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with pytest.raises(typer.Exit):
                release_command()


# ──────────────────────────────────────────────
# Test 15: Release with Existing Remote Tag
# ──────────────────────────────────────────────


class TestReleaseExistingRemoteTag:
    """Test 15: Release fails when tag already exists on remote."""

    def test_release_tag_exists_remotely_fails(self, e2e_project):
        """Release should fail if tag already exists on remote."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=True,
            tag_exists_remotely=True,
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with pytest.raises(typer.Exit):
                release_command()


# ──────────────────────────────────────────────
# Bug Fix Tests: Dry-run version calculation
# ──────────────────────────────────────────────


class TestDryRunVersionCalculation:
    """Tests for the bug fix where dry-run with bump used wrong version for tag."""

    def test_release_bump_dry_run_uses_new_version_for_tag(self, e2e_project):
        """After dry-run bump, release should use the NEW version for tag, not old."""
        # The bug: release --bump MINOR --dry-run would read old version from file
        # and look for tag v0.1.0 instead of v0.2.0

        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="0.2.0",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command"):
                # This should succeed - it should look for tag v0.2.0, not v0.1.0
                release_command(bump_type="MINOR", push=True, dry_run=True)

        # Original version should be unchanged
        assert get_current_version(Language.PYTHON) == "0.1.0"

    def test_dry_run_skips_clean_working_tree_check(self, e2e_project):
        """Dry-run should not fail due to dirty working tree."""
        # Create uncommitted changes
        (e2e_project / "dirty.txt").write_text("dirty")
        subprocess.run([GIT, "add", "dirty.txt"], check=True, capture_output=True)

        mock_git = _make_mock_git_for_release(
            tag_exists_locally=True,
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.typer.confirm", return_value=True):
                # Should NOT fail even with dirty working tree in dry-run
                release_command(dry_run=True)

    def test_dry_run_bump_skips_tag_validation(self, e2e_project):
        """Dry-run with bump should not require tag to exist yet."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="0.2.0",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command"):
                # Should succeed: tag v0.2.0 doesn't exist yet, but that's OK in dry-run
                release_command(bump_type="MINOR", push=True, dry_run=True)


# ──────────────────────────────────────────────
# --with-bump Feature Tests
# ──────────────────────────────────────────────


class TestWithBumpFlag:
    """Tests for the --with-bump interactive release flag."""

    def test_with_bump_prompts_for_type(self, e2e_project):
        """--with-bump should prompt user for bump type (same as bump command)."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="0.2.0",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command"):
                with patch("questionary.select") as mock_select:
                    mock_select.return_value.ask.return_value = "Minor (0.1.0 -> 0.2.0)"
                    release_command(with_bump=True, push=True, dry_run=True)

        mock_select.assert_called_once()

    def test_with_bump_dry_run_full_flow(self, e2e_project):
        """--with-bump --push --dry-run: full interactive flow."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="0.2.0",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command") as mock_bump:
                with patch("questionary.select") as mock_select:
                    mock_select.return_value.ask.return_value = "Minor (0.1.0 -> 0.2.0)"
                    release_command(with_bump=True, push=True, dry_run=True)

        mock_bump.assert_called_once()

    def test_with_bump_non_interactive_defaults_to_patch(self, e2e_project):
        """--with-bump in non-interactive mode without --bump should default to PATCH."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="0.1.1",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command") as mock_bump:
                release_command(with_bump=True, non_interactive=True, push=True, dry_run=True)

        mock_bump.assert_called_once()
        # Should have been called with BumpOptions containing the explicit version string
        call_args = mock_bump.call_args[0]
        options = call_args[0]
        assert isinstance(options, BumpOptions)
        assert options.version == "0.1.1"

    def test_with_bump_user_cancels_selection(self, e2e_project):
        """--with-bump: user cancels bump type selection."""
        mock_git = _make_mock_git_for_release(tag_exists_locally=True)

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.typer.confirm", return_value=True):
                with patch("questionary.select") as mock_select:
                    mock_select.return_value.ask.return_value = None
                    # Should proceed without bump
                    release_command(with_bump=True, dry_run=True)

    def test_with_bump_explicit_type_takes_priority(self, e2e_project):
        """--bump MAJOR takes priority over --with-bump."""
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="1.0.0",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command") as mock_bump:
                # --bump MAJOR should take priority, --with-bump should not trigger prompt
                release_command(bump_type="MAJOR", with_bump=True, push=True, dry_run=True)

        mock_bump.assert_called_once()
        # Should have been called with BumpOptions containing the explicit version string
        call_args = mock_bump.call_args[0]
        options = call_args[0]
        assert isinstance(options, BumpOptions)
        assert options.version == "1.0.0"

    def test_with_bump_eoferror_handled(self, e2e_project):
        """--with-bump should handle EOFError gracefully (non-tty)."""
        mock_git = _make_mock_git_for_release(tag_exists_locally=True)

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.typer.confirm", return_value=True):
                with patch("questionary.select") as mock_select:
                    mock_select.return_value.ask.side_effect = EOFError
                    # Should not crash, just skip bump
                    release_command(with_bump=True, dry_run=True)


# ──────────────────────────────────────────────
# _get_bump_type_interactively Tests
# ──────────────────────────────────────────────


class TestGetBumpTypeInteractively:
    """Tests for _get_bump_type_interactively with with_bump parameter."""

    def test_explicit_bump_type_takes_priority(self, e2e_project):
        """Explicit bump_type should be converted to version string."""
        should_bump, new_version = _get_bump_type_interactively(
            non_interactive=False, bump_type="MINOR", dry_run=False, with_bump=False
        )
        assert should_bump is True
        assert new_version == "0.2.0"

    def test_with_bump_non_interactive_defaults_patch(self, e2e_project):
        """with_bump + non_interactive should default to patch version."""
        should_bump, new_version = _get_bump_type_interactively(
            non_interactive=True, bump_type=None, dry_run=True, with_bump=True
        )
        assert should_bump is True
        assert new_version == "0.1.1"

    def test_dry_run_without_with_bump_skips_prompts(self):
        """dry_run without with_bump should not prompt."""
        should_bump, bump_type = _get_bump_type_interactively(
            non_interactive=False, bump_type=None, dry_run=True, with_bump=False
        )
        assert should_bump is False
        assert bump_type is None

    def test_with_bump_prompts_interactively(self, e2e_project):
        """with_bump should use bump's interactive selection."""
        with patch("questionary.select") as mock_select:
            mock_select.return_value.ask.return_value = "Minor (0.1.0 -> 0.2.0)"
            should_bump, new_version = _get_bump_type_interactively(
                non_interactive=False, bump_type=None, dry_run=True, with_bump=True
            )
        assert should_bump is True
        assert new_version == "0.2.0"


# ──────────────────────────────────────────────
# CLI Integration Tests
# ──────────────────────────────────────────────


class TestCLIIntegration:
    """Tests for CLI command invocation via typer runner."""

    def test_release_with_bump_cli_flag(self, monkeypatch):
        """Test --with-bump flag is passed correctly via CLI."""
        from typer.testing import CliRunner

        from rhiza_tools.cli import app

        runner = CliRunner()
        mock_release = MagicMock()
        monkeypatch.setattr("rhiza_tools.cli.release_command", mock_release)

        result = runner.invoke(app, ["release", "--with-bump", "--push", "--dry-run"])
        assert result.exit_code == 0
        mock_release.assert_called_once_with(None, True, True, False, True)

    def test_release_bump_and_with_bump_cli(self, monkeypatch):
        """Test --bump MINOR --with-bump together via CLI."""
        from typer.testing import CliRunner

        from rhiza_tools.cli import app

        runner = CliRunner()
        mock_release = MagicMock()
        monkeypatch.setattr("rhiza_tools.cli.release_command", mock_release)

        result = runner.invoke(app, ["release", "--bump", "MINOR", "--with-bump", "--push"])
        assert result.exit_code == 0
        mock_release.assert_called_once_with("MINOR", True, False, False, True)

    def test_bump_cli_all_flags(self, monkeypatch):
        """Test bump CLI with all flags."""
        from typer.testing import CliRunner

        from rhiza_tools.cli import app

        runner = CliRunner()
        mock_bump = MagicMock()
        monkeypatch.setattr("rhiza_tools.cli.bump_command", mock_bump)

        result = runner.invoke(
            app,
            ["bump", "minor", "--dry-run", "--commit", "--push", "--allow-dirty"],
        )
        assert result.exit_code == 0
        # bump_command should be called with a BumpOptions object
        assert mock_bump.call_count == 1
        options = mock_bump.call_args[0][0]
        assert isinstance(options, BumpOptions)
        assert options.version == "minor"
        assert options.dry_run is True
        assert options.commit is True
        assert options.push is True
        assert options.branch is None
        assert options.allow_dirty is True


# ──────────────────────────────────────────────
# Sequential Bump-Then-Release E2E
# ──────────────────────────────────────────────


class TestSequentialBumpRelease:
    """Test complete bump -> release workflows."""

    def test_bump_then_release_dry_run(self, e2e_project):
        """Bump patch, then release dry-run."""
        # Step 1: Actually bump the version
        bump_command(BumpOptions(version="patch", commit=True))
        assert get_current_version(Language.PYTHON) == "0.1.1"

        # Step 2: Verify tag was created by bump-my-version (safe - runs in temp repo)
        result = subprocess.run([GIT, "tag", "-l", "v0.1.1"], capture_output=True, text=True, check=True)
        assert "v0.1.1" in result.stdout

        # Step 3: Release dry-run
        mock_git = _make_mock_git_for_release(
            tag_exists_locally=True,
            tag_exists_remotely=False,
            version="0.1.1",
        )
        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.typer.confirm", return_value=True):
                release_command(dry_run=True)

    def test_bump_minor_then_release(self, e2e_project):
        """Bump minor, then release dry-run."""
        bump_command(BumpOptions(version="minor", commit=True))
        assert get_current_version(Language.PYTHON) == "0.2.0"

        # Verify tag was created (safe - runs in temp repo)
        result = subprocess.run([GIT, "tag", "-l", "v0.2.0"], capture_output=True, text=True, check=True)
        assert "v0.2.0" in result.stdout

    def test_multiple_bumps(self, e2e_project):
        """Multiple sequential bumps work correctly."""
        bump_command(BumpOptions(version="patch"))
        assert get_current_version(Language.PYTHON) == "0.1.1"

        bump_command(BumpOptions(version="patch"))
        assert get_current_version(Language.PYTHON) == "0.1.2"

        bump_command(BumpOptions(version="minor"))
        assert get_current_version(Language.PYTHON) == "0.2.0"

        bump_command(BumpOptions(version="major"))
        assert get_current_version(Language.PYTHON) == "1.0.0"

    def test_bump_prerelease_then_release_candidate(self, e2e_project):
        """Bump through prerelease types."""
        bump_command(BumpOptions(version="alpha"))
        assert get_current_version(Language.PYTHON) == "0.1.1-alpha.1"

        bump_command(BumpOptions(version="beta"))
        assert get_current_version(Language.PYTHON) == "0.1.1-beta.1"

        bump_command(BumpOptions(version="rc"))
        assert get_current_version(Language.PYTHON) == "0.1.1-rc.1"


# ──────────────────────────────────────────────
# Non-default Branch Release
# ──────────────────────────────────────────────


class TestNonDefaultBranchRelease:
    """Test releasing from non-default branch."""

    def test_release_from_feature_branch_dry_run(self, e2e_project):
        """Release from non-default branch should show warning."""
        subprocess.run([GIT, "tag", "v0.1.0"], check=True, capture_output=True)

        mock_git = _make_mock_git_for_release(
            current_branch="feature-branch",
            default_branch="main",
            tag_exists_locally=True,
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.typer.confirm", return_value=True):
                release_command(dry_run=True)

    def test_release_bump_from_non_default_branch_dry_run(self, e2e_project):
        """Bump + release from non-default branch in dry-run."""
        mock_git = _make_mock_git_for_release(
            current_branch="feature-branch",
            default_branch="main",
            tag_exists_locally=False,
            tag_exists_remotely=False,
            version="0.2.0",
        )

        with patch("rhiza_tools.commands.release.run_git_command", side_effect=mock_git):
            with patch("rhiza_tools.commands.release.bump_command"):
                release_command(bump_type="MINOR", push=True, dry_run=True)
