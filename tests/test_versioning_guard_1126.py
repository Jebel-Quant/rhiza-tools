"""Regression tests for issue #1126: releasing an older version.

These cover the three layers of the fix:

* ``get_latest_remote_version`` — read the highest semver tag from the remote.
* ``_resolve_bump_baseline`` / ``bump_command`` — never bump from a stale local
  version that is behind the remote.
* ``_check_release_version_monotonic`` / ``release_command`` — refuse to release
  a version that is not strictly newer than the latest remote release, unless
  ``--allow-older`` is given.
"""

from unittest.mock import MagicMock, patch

import pytest
import semver
import typer

from rhiza_tools.commands import bump as bump_mod
from rhiza_tools.commands import release as release_mod
from rhiza_tools.commands._shared import get_latest_remote_version
from rhiza_tools.commands.bump import BumpOptions, Language, _resolve_bump_baseline, bump_command, get_current_version

_BUMPVERSION_CFG = """
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


@pytest.fixture
def bump_project(temp_project):
    """A project with a minimal bumpversion config (self-contained for this module)."""
    rhiza_dir = temp_project / ".rhiza"
    rhiza_dir.mkdir(exist_ok=True)
    (rhiza_dir / ".cfg.toml").write_text(_BUMPVERSION_CFG)
    return temp_project


def _ls_remote(*tags: str) -> MagicMock:
    """Build a fake ``git ls-remote --tags`` CompletedProcess for *tags*."""
    lines = "\n".join(f"0000000000000000000000000000000000000000\trefs/tags/{t}" for t in tags)
    return MagicMock(returncode=0, stdout=lines + "\n")


# ── get_latest_remote_version ─────────────────────────────────────────────────


def test_latest_remote_version_picks_highest():
    """The highest semver tag wins, regardless of listing order."""
    with patch(
        "rhiza_tools.commands._shared.run_git_command",
        return_value=_ls_remote("v0.3.2", "v0.10.0", "v0.4.0"),
    ):
        assert get_latest_remote_version() == semver.Version.parse("0.10.0")


def test_latest_remote_version_ignores_non_semver_and_peeled_refs():
    """Non-semver tags and peeled ``^{}`` duplicates are ignored, not fatal."""
    listing = MagicMock(
        returncode=0,
        stdout=(
            "sha\trefs/tags/v1.0.0\n"
            "sha\trefs/tags/v1.0.0^{}\n"  # peeled duplicate of an annotated tag
            "sha\trefs/tags/latest\n"  # not a version
            "sha\trefs/heads/main\n"  # not a tag at all
        ),
    )
    with patch("rhiza_tools.commands._shared.run_git_command", return_value=listing):
        assert get_latest_remote_version() == semver.Version.parse("1.0.0")


@pytest.mark.parametrize(
    "result",
    [
        MagicMock(returncode=128, stdout=""),  # no remote / network error
        MagicMock(returncode=0, stdout="   \n"),  # remote reachable but no tags
    ],
)
def test_latest_remote_version_returns_none_when_unavailable(result):
    """Degrade gracefully to None when the remote can't be read or has no tags."""
    with patch("rhiza_tools.commands._shared.run_git_command", return_value=result):
        assert get_latest_remote_version() is None


# ── _resolve_bump_baseline ────────────────────────────────────────────────────


def test_baseline_uses_remote_when_local_is_stale(monkeypatch):
    """The exact #1126 scenario: local 0.3.2, remote 0.4.0 -> bump from 0.4.0."""
    monkeypatch.setattr(bump_mod, "get_latest_remote_version", lambda *a, **k: semver.Version.parse("0.4.0"))
    assert _resolve_bump_baseline("0.3.2") == "0.4.0"


def test_baseline_keeps_local_when_ahead_of_remote(monkeypatch):
    """A local version newer than the remote is kept as the baseline."""
    monkeypatch.setattr(bump_mod, "get_latest_remote_version", lambda *a, **k: semver.Version.parse("0.4.0"))
    assert _resolve_bump_baseline("0.5.0") == "0.5.0"


def test_baseline_falls_back_to_local_when_remote_unknown(monkeypatch):
    """Offline / no remote -> use the local version unchanged (autouse stub)."""
    assert _resolve_bump_baseline("0.3.2") == "0.3.2"


def test_baseline_uses_remote_when_local_version_is_unparseable(monkeypatch):
    """An unparseable local version falls back to the remote tag as the baseline.

    A corrupt or non-semver ``version`` in pyproject.toml must not crash the bump
    or let a relative bump compute from nothing — the remote tag is authoritative.
    """
    monkeypatch.setattr(bump_mod, "get_latest_remote_version", lambda *a, **k: semver.Version.parse("0.4.0"))
    assert _resolve_bump_baseline("not-a-semver") == "0.4.0"


def test_bump_patch_from_stale_branch_jumps_past_remote(bump_project, monkeypatch):
    """End-to-end: `bump patch` on a stale 0.3.2 branch yields 0.4.1, not 0.3.3."""
    pyproject = bump_project / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-project"\nversion = "0.3.2"\n')
    monkeypatch.setattr(bump_mod, "get_latest_remote_version", lambda *a, **k: semver.Version.parse("0.4.0"))

    bump_command(BumpOptions(version="patch"))

    assert get_current_version(Language.PYTHON) == "0.4.1"


# ── _check_release_version_monotonic ──────────────────────────────────────────


def _patch_remote_latest(monkeypatch, version: str | None):
    """Patch helper _patch_remote_latest for the test."""
    monkeypatch.setattr(
        release_mod,
        "get_latest_remote_version",
        lambda *a, **k: semver.Version.parse(version) if version else None,
    )


def test_monotonic_allows_newer(monkeypatch):
    """A strictly newer version passes the guard."""
    _patch_remote_latest(monkeypatch, "0.4.0")
    release_mod._check_release_version_monotonic("0.4.1", allow_older=False)  # no raise


@pytest.mark.parametrize("candidate", ["0.3.4", "0.4.0"])
def test_monotonic_blocks_older_or_equal(monkeypatch, candidate):
    """Older or equal versions are rejected without --allow-older."""
    _patch_remote_latest(monkeypatch, "0.4.0")
    with pytest.raises(typer.Exit):
        release_mod._check_release_version_monotonic(candidate, allow_older=False)


def test_monotonic_allow_older_override(monkeypatch):
    """--allow-older downgrades the block to a warning (maintenance release)."""
    _patch_remote_latest(monkeypatch, "0.4.0")
    release_mod._check_release_version_monotonic("0.3.4", allow_older=True)  # no raise


def test_monotonic_skipped_when_no_remote_tags(monkeypatch):
    """First release (no remote tags) is always allowed."""
    _patch_remote_latest(monkeypatch, None)
    release_mod._check_release_version_monotonic("0.1.0", allow_older=False)  # no raise


def test_monotonic_rejects_unparseable_candidate(monkeypatch):
    """An unparseable candidate version is a hard error, not a silent pass.

    Once a remote release exists the guard must be able to compare against it; a
    version string it cannot parse is treated as a fatal misconfiguration.
    """
    _patch_remote_latest(monkeypatch, "0.4.0")
    with pytest.raises(typer.Exit) as excinfo:
        release_mod._check_release_version_monotonic("not-a-semver", allow_older=False)
    assert excinfo.value.exit_code == 1


# ── release_command integration ───────────────────────────────────────────────


def _release_git_mock():
    """Minimal git mock sufficient to reach the monotonicity guard in dry-run."""

    def mock_run_git_command(cmd, check=True):
        """Stand in for run_git_command during the test."""
        result = MagicMock(returncode=0, stdout="")
        if "rev-parse" in cmd and "--abbrev-ref" in cmd:
            result.stdout = "feature/diverged"
        elif "remote" in cmd and "show" in cmd:
            result.stdout = "* remote origin\n  HEAD branch: main\n"
        elif "ls-remote" in cmd:
            result.returncode = 1  # tag does not exist on remote
        return result

    return mock_run_git_command


def test_release_blocks_stale_version(tmp_path, monkeypatch):
    """Release on a stale 0.3.2 checkout is blocked when remote already has 0.4.0."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "p"\nversion = "0.3.2"\n')
    monkeypatch.chdir(tmp_path)
    _patch_remote_latest(monkeypatch, "0.4.0")

    with (
        patch("rhiza_tools.commands.release_git.run_git_command", side_effect=_release_git_mock()),
        pytest.raises(typer.Exit),
    ):
        release_mod.release_command(non_interactive=True, dry_run=True)


def test_release_allows_stale_version_with_override(tmp_path, monkeypatch):
    """--allow-older lets the same stale release through (back-branch maintenance)."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "p"\nversion = "0.3.2"\n')
    monkeypatch.chdir(tmp_path)
    _patch_remote_latest(monkeypatch, "0.4.0")

    with (
        patch("rhiza_tools.commands.release_git.run_git_command", side_effect=_release_git_mock()),
        patch("rhiza_tools.commands.release_versioning.bump_command"),
    ):
        # Should complete the dry-run without raising for the monotonicity guard.
        release_mod.release_command(non_interactive=True, dry_run=True, allow_older=True)
