"""Unit and CLI tests for the suppression-audit command and its modules."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from rhiza_tools.cli import app
from rhiza_tools.commands.suppression import parse, report, suppression_audit_command

runner = CliRunner()

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI colour escape codes so output can be asserted on plainly."""
    return _ANSI.sub("", text)


# ---------------------------------------------------------------------------
# CVE extraction and pip-audit parsing
# ---------------------------------------------------------------------------


def test_nosec_cves_extracts_only_nosec_entries():
    """Only # nosec suppressions with CVE tags should be captured."""
    suppressions = [
        parse.Suppression(file="a.py", line_no=1, kind="nosec", raw="# nosec B101 CVE-2024-1234"),
        parse.Suppression(file="b.py", line_no=2, kind="noqa", raw="# noqa: E501 CVE-2024-0001"),
        parse.Suppression(file="c.py", line_no=3, kind="nosec", raw="# nosec B602"),
    ]
    assert parse.nosec_cves(suppressions) == {"CVE-2024-1234"}


def test_active_pip_audit_ids_collects_ids_and_aliases(monkeypatch):
    """pip-audit JSON IDs and aliases should be normalized and returned."""
    payload = """
    {"dependencies": [{"name": "pkg", "vulns": [{"id": "PYSEC-1", "aliases": ["CVE-2024-1111"]}]}]}
    """
    monkeypatch.setattr(
        report.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=payload, stderr=""),
    )
    assert report._active_pip_audit_ids([]) == {"PYSEC-1", "CVE-2024-1111"}


def test_active_pip_audit_ids_raises_on_unexpected_returncode(monkeypatch, capsys):
    """A return code outside {0, 1} should surface a RuntimeError and echo output."""
    monkeypatch.setattr(
        report.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stdout="boom-out", stderr="boom-err"),
    )
    with pytest.raises(RuntimeError, match="pip-audit execution failed"):
        report._active_pip_audit_ids([])
    captured = capsys.readouterr()
    assert "boom-out" in captured.out
    assert "boom-err" in captured.err


def test_active_pip_audit_ids_raises_on_invalid_json(monkeypatch):
    """Non-JSON pip-audit output should raise a descriptive RuntimeError."""
    monkeypatch.setattr(
        report.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="not-json", stderr=""),
    )
    with pytest.raises(RuntimeError, match="did not return valid JSON"):
        report._active_pip_audit_ids([])


# ---------------------------------------------------------------------------
# Scanning helpers
# ---------------------------------------------------------------------------


def test_should_skip_matches_skip_dirs():
    """Paths inside a skip-listed directory should be skipped."""
    assert parse._should_skip(Path(".venv") / "lib" / "mod.py") is True
    assert parse._should_skip(Path("tests") / "test_mod.py") is True
    assert parse._should_skip(Path("src") / "pkg" / "mod.py") is False


def test_is_rhiza_repo_detects_template_marker(tmp_path):
    """A project with .rhiza/template.yml is a consumer repo, otherwise the framework repo."""
    assert parse._is_rhiza_repo(tmp_path) is True
    (tmp_path / ".rhiza").mkdir()
    (tmp_path / ".rhiza" / "template.yml").write_text("upstream: x\n", encoding="utf-8")
    assert parse._is_rhiza_repo(tmp_path) is False


def test_scan_file_detects_every_suppression_kind(tmp_path):
    """scan_file should classify each suppression family and capture its codes."""
    target = tmp_path / "sample.py"
    target.write_text(
        "\n".join(
            [
                "x = 1  # noqa: E501, F401",
                "y = 2  # nosec B101",
                "z: int = 3  # type: ignore[assignment]",
                "w = 4  # pragma: no cover",
                "v = 5  # noinspection PyUnresolvedReferences",
                "ok = 6  # just a normal comment",
            ]
        ),
        encoding="utf-8",
    )
    found = {sup.kind: sup for sup in parse.scan_file(target)}
    assert found["noqa"].codes == ["E501", "F401"]
    assert found["nosec"].codes == ["B101"]
    assert found["type:ignore"].codes == ["assignment"]
    assert found["no cover"].codes == []
    assert found["noinspection"].codes == ["PyUnresolvedReferences"]
    assert "just a normal comment" not in {s.raw for s in parse.scan_file(target)}


def test_scan_file_returns_empty_for_unreadable_file(tmp_path):
    """A missing file should yield no suppressions rather than raising."""
    assert parse.scan_file(tmp_path / "does-not-exist.py") == []


def test_scan_file_swallows_tokenize_errors(tmp_path):
    """A file that fails to tokenize should be skipped without raising."""
    broken = tmp_path / "broken.py"
    broken.write_text('x = "unterminated  # noqa: E501\n', encoding="utf-8")
    assert isinstance(parse.scan_file(broken), list)


def test_count_non_empty_lines(tmp_path):
    """Only lines with non-whitespace content should be counted."""
    target = tmp_path / "lines.py"
    target.write_text("a = 1\n\n   \nb = 2\n", encoding="utf-8")
    assert parse.count_non_empty_lines(target) == 2
    assert parse.count_non_empty_lines(tmp_path / "missing.py") == 0


# ---------------------------------------------------------------------------
# Grading and rendering
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("density", "expected"),
    [(0.0, "A+"), (0.5, "A"), (1.0, "B"), (2.0, "C"), (3.0, "D"), (10.0, "F")],
)
def test_compute_grade_thresholds(density, expected):
    """Grades should map to the documented density thresholds."""
    assert parse.compute_grade(density) == expected


def test_bar_renders_fixed_width():
    """The histogram bar is always _BAR_WIDTH wide, all-empty when max is zero."""
    assert report._bar(0, 0) == "░" * report._BAR_WIDTH
    bar = report._bar(5, 10)
    assert len(bar) == report._BAR_WIDTH
    assert "█" in bar
    assert "░" in bar


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def test_collect_suppressions_includes_rhiza_dir_in_framework_repo(tmp_path):
    """In the framework repo (no template.yml) .rhiza/ files are scanned."""
    (tmp_path / ".rhiza" / "utils").mkdir(parents=True)
    (tmp_path / "app.py").write_text("a = 1  # noqa: E501\n", encoding="utf-8")
    (tmp_path / ".rhiza" / "utils" / "helper.py").write_text("b = 2  # nosec B101\n", encoding="utf-8")

    py_files, suppressions, total_lines = parse.collect_suppressions(tmp_path)
    scanned = {Path(s.file).name for s in suppressions}
    assert scanned == {"app.py", "helper.py"}
    assert total_lines == 2
    assert len(py_files) == 2


def test_collect_suppressions_skips_files_in_skip_dirs(tmp_path):
    """Python files inside skip-listed directories (e.g. tests/) are excluded from the scan."""
    (tmp_path / "tests").mkdir()
    (tmp_path / "app.py").write_text("a = 1  # noqa: E501\n", encoding="utf-8")
    (tmp_path / "tests" / "test_app.py").write_text("b = 2  # nosec B101\n", encoding="utf-8")

    py_files, suppressions, _total = parse.collect_suppressions(tmp_path)
    assert {Path(s.file).name for s in suppressions} == {"app.py"}
    assert {p.name for p in py_files} == {"app.py"}


def test_collect_suppressions_skips_rhiza_dir_in_consumer_repo(tmp_path):
    """In a consumer repo (template.yml present) the .rhiza/ tree is excluded."""
    (tmp_path / ".rhiza").mkdir()
    (tmp_path / ".rhiza" / "template.yml").write_text("upstream: x\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("a = 1  # noqa: E501\n", encoding="utf-8")
    (tmp_path / ".rhiza" / "framework.py").write_text("b = 2  # nosec B101\n", encoding="utf-8")

    _py_files, suppressions, _total = parse.collect_suppressions(tmp_path)
    assert {Path(s.file).name for s in suppressions} == {"app.py"}


def test_print_report_with_suppressions(capsys):
    """The report should render details, a histogram, and a grade when suppressions exist."""
    suppressions = [
        parse.Suppression(file="app.py", line_no=10, kind="noqa", codes=["E501"], raw="# noqa: E501"),
        parse.Suppression(file="app.py", line_no=20, kind="nosec", codes=[], raw="# nosec"),
    ]
    report.print_report([Path("app.py")], suppressions, total_lines=100)

    out = _strip_ansi(capsys.readouterr().out)
    assert "Suppression Audit Report" in out
    assert "app.py:10: # noqa[E501]" in out
    assert "Histogram (by suppression code):" in out
    assert "noqa[E501]" in out
    assert "Grade" in out
    assert "Suppressions    : 2" in out


def test_print_report_without_suppressions(capsys):
    """A clean codebase should report no suppressions and an empty histogram."""
    report.print_report([Path("app.py")], [], total_lines=0)
    out = _strip_ansi(capsys.readouterr().out)
    assert "No inline suppressions found." in out
    assert "(none)" in out


# ---------------------------------------------------------------------------
# Stale-CVE gate
# ---------------------------------------------------------------------------


def test_check_stale_nosec_cves_no_suppressions(capsys):
    """With no CVE-tagged # nosec comments the check passes without calling pip-audit."""
    assert report.check_stale_nosec_cves([], []) == 0
    assert "No CVE-tagged # nosec suppressions found." in _strip_ansi(capsys.readouterr().out)


def test_check_stale_nosec_cves_flags_stale(monkeypatch, capsys):
    """A suppressed CVE that pip-audit no longer reports is flagged as stale."""
    suppressions = [parse.Suppression(file="a.py", line_no=1, kind="nosec", raw="# nosec B101 CVE-2024-1234")]
    monkeypatch.setattr(report, "_active_pip_audit_ids", lambda _args: set())
    assert report.check_stale_nosec_cves(suppressions, []) == 1
    assert "Stale # nosec CVE suppressions detected:" in _strip_ansi(capsys.readouterr().out)


def test_check_stale_nosec_cves_all_active(monkeypatch, capsys):
    """A suppressed CVE that pip-audit still reports is considered current."""
    suppressions = [parse.Suppression(file="a.py", line_no=1, kind="nosec", raw="# nosec B101 CVE-2024-1234")]
    monkeypatch.setattr(report, "_active_pip_audit_ids", lambda _args: {"CVE-2024-1234"})
    assert report.check_stale_nosec_cves(suppressions, []) == 0
    assert "match active pip-audit findings." in _strip_ansi(capsys.readouterr().out)


def test_check_stale_nosec_cves_pip_audit_failure(monkeypatch, capsys):
    """A pip-audit RuntimeError should surface as exit code 2."""
    suppressions = [parse.Suppression(file="a.py", line_no=1, kind="nosec", raw="# nosec B101 CVE-2024-1234")]
    monkeypatch.setattr(
        report.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stdout="", stderr=""),
    )
    assert report.check_stale_nosec_cves(suppressions, []) == 2
    assert "pip-audit execution failed" in _strip_ansi(capsys.readouterr().out)


# ---------------------------------------------------------------------------
# Orchestrator + CLI
# ---------------------------------------------------------------------------


def test_command_reports_and_returns_zero(monkeypatch, tmp_path, capsys):
    """A plain run scans the working tree, prints the report, and returns 0."""
    (tmp_path / "app.py").write_text("a = 1  # noqa: E501\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert suppression_audit_command(fail_stale_nosec_cve=False, pip_audit_args=[]) == 0
    assert "Suppression Audit Report" in _strip_ansi(capsys.readouterr().out)


def test_command_with_stale_gate_returns_one(monkeypatch, tmp_path, capsys):
    """The stale-CVE gate fails when a suppressed CVE is no longer active."""
    (tmp_path / "app.py").write_text("a = 1  # nosec B101 CVE-2024-9999\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(report, "_active_pip_audit_ids", lambda _args: set())

    assert suppression_audit_command(fail_stale_nosec_cve=True, pip_audit_args=[]) == 1
    assert "Stale # nosec CVE suppressions detected:" in _strip_ansi(capsys.readouterr().out)


def test_cli_reports_and_exits_zero(monkeypatch, tmp_path):
    """The CLI scans the working tree and exits 0 on a plain run."""
    (tmp_path / "app.py").write_text("a = 1  # noqa: E501\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["suppression-audit"])
    assert result.exit_code == 0
    assert "Suppression Audit Report" in _strip_ansi(result.output)


def test_cli_stale_gate_exits_one(monkeypatch, tmp_path):
    """The CLI --fail-stale-nosec-cve flag maps a stale finding to exit code 1."""
    (tmp_path / "app.py").write_text("a = 1  # nosec B101 CVE-2024-9999\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(report, "_active_pip_audit_ids", lambda _args: set())

    result = runner.invoke(app, ["suppression-audit", "--fail-stale-nosec-cve"])
    assert result.exit_code == 1
