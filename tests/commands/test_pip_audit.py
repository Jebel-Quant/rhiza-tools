"""Unit and CLI tests for the pip-audit command."""

from __future__ import annotations

import json
import re
from types import SimpleNamespace

from typer.testing import CliRunner

from rhiza_tools.cli import app
from rhiza_tools.commands import pip_audit

runner = CliRunner()

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Remove ANSI colour escape codes so output can be asserted on plainly."""
    return _ANSI.sub("", text)


# ---------------------------------------------------------------------------
# _vuln_ids
# ---------------------------------------------------------------------------


def test_vuln_ids_includes_primary_id_and_distinct_aliases():
    """Vulnerability identifiers should include the primary ID and unique aliases."""
    vuln = {"id": "PYSEC-2024-1", "aliases": ["CVE-2024-1234", "PYSEC-2024-1", "GHSA-xxxx-yyyy"]}
    assert pip_audit._vuln_ids(vuln) == "PYSEC-2024-1, CVE-2024-1234, GHSA-xxxx-yyyy"


# ---------------------------------------------------------------------------
# pip_audit_command
# ---------------------------------------------------------------------------


def test_command_returns_zero_and_forwards_args_when_audit_passes(monkeypatch, capsys):
    """A passing pip-audit run prints OK, returns zero, and forwards extra args."""
    seen: dict[str, list[str]] = {}

    def _fake_run(cmd, *, capture_output, text, check):
        """Record the invoked command and return a passing (returncode 0) result."""
        seen["cmd"] = cmd
        assert capture_output is True
        assert text is True
        assert check is False
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pip_audit.shutil, "which", lambda name: "/custom/uvx")
    monkeypatch.setattr(pip_audit.subprocess, "run", _fake_run)

    assert pip_audit.pip_audit_command(["--ignore-vuln", "CVE-2024-1234"]) == 0
    assert seen["cmd"] == ["/custom/uvx", "pip-audit", "--format", "json", "--ignore-vuln", "CVE-2024-1234"]
    assert "[OK] pip-audit: no vulnerabilities found" in _strip_ansi(capsys.readouterr().out)


def test_command_echoes_raw_output_when_json_parsing_fails(monkeypatch, capsys):
    """Non-JSON output is passed through unchanged and preserves the exit code."""
    monkeypatch.setattr(
        pip_audit.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=2, stdout="oops\n", stderr="bad\n"),
    )

    assert pip_audit.pip_audit_command([]) == 2
    captured = capsys.readouterr()
    assert captured.out == "oops\n"
    assert captured.err == "bad\n"


def test_command_warns_for_tooling_vulnerabilities_without_failing(monkeypatch, capsys):
    """Tooling-package vulnerabilities warn but still return success."""
    payload = {
        "dependencies": [
            {"name": "pip", "version": "24.0", "vulns": [{"id": "PYSEC-2024-1", "aliases": ["CVE-2024-1234"]}]}
        ]
    }
    monkeypatch.setattr(
        pip_audit.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=json.dumps(payload), stderr=""),
    )

    assert pip_audit.pip_audit_command([]) == 0
    output = _strip_ansi(capsys.readouterr().out)
    assert "[WARN] pip==24.0: PYSEC-2024-1, CVE-2024-1234 (tooling — not failing build)" in output
    assert "[FAIL]" not in output


def test_command_fails_for_runtime_vulnerabilities_and_warns_for_tooling(monkeypatch, capsys):
    """Runtime-package vulnerabilities fail even when tooling warnings are present."""
    payload = {
        "dependencies": [
            {"name": "setuptools", "version": "70.0", "vulns": [{"id": "PYSEC-2024-2", "aliases": []}]},
            {"name": "requests", "version": "2.0.0", "vulns": [{"id": "GHSA-abcd", "aliases": ["CVE-2024-5678"]}]},
        ]
    }
    monkeypatch.setattr(pip_audit.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        pip_audit.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=json.dumps(payload), stderr=""),
    )

    assert pip_audit.pip_audit_command([]) == 1
    output = _strip_ansi(capsys.readouterr().out)
    assert "[WARN] setuptools==70.0: PYSEC-2024-2 (tooling — not failing build)" in output
    assert "[FAIL] requests==2.0.0: GHSA-abcd, CVE-2024-5678" in output


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_forwards_extra_args_and_exits_zero(monkeypatch):
    """The CLI forwards trailing args to pip-audit and maps a clean run to exit 0."""
    seen: dict[str, list[str]] = {}

    def _fake_run(cmd, **kwargs):
        """Capture the command pip-audit would run and report a clean result."""
        seen["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(pip_audit.shutil, "which", lambda name: "uvx")
    monkeypatch.setattr(pip_audit.subprocess, "run", _fake_run)

    result = runner.invoke(app, ["pip-audit", "--ignore-vuln", "CVE-2024-1234"])
    assert result.exit_code == 0
    assert seen["cmd"] == ["uvx", "pip-audit", "--format", "json", "--ignore-vuln", "CVE-2024-1234"]


def test_cli_exit_code_reflects_runtime_vulnerability(monkeypatch):
    """A runtime vulnerability makes the CLI exit non-zero."""
    payload = {"dependencies": [{"name": "requests", "version": "2.0.0", "vulns": [{"id": "GHSA-abcd"}]}]}
    monkeypatch.setattr(
        pip_audit.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=json.dumps(payload), stderr=""),
    )

    result = runner.invoke(app, ["pip-audit"])
    assert result.exit_code == 1


def test_cli_help_lists_command():
    """The pip-audit command exposes help text."""
    result = runner.invoke(app, ["pip-audit", "--help"])
    assert result.exit_code == 0
    assert "pip-audit" in result.stdout
