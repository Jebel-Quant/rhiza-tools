"""Suppression audit: scan the codebase for inline suppressions and grade them.

Detects and reports on inline suppression comments such as:

- ``# noqa`` / ``# noqa: CODE`` (ruff/flake8 linting suppressions)
- ``# nosec`` / ``# nosec: CODE`` (bandit security suppressions)
- ``# type: ignore`` / ``# type: ignore[CODE]`` (mypy/pyright type suppressions)
- ``# pragma: no cover`` (coverage suppressions)
- ``# noinspection CODE`` (PyCharm/IDE suppressions)

Outputs a detailed per-file report, an ASCII histogram, and a letter grade.

This package is the thin orchestrator. Parsing lives in
:mod:`rhiza_tools.commands.suppression.parse` and reporting/output lives in
:mod:`rhiza_tools.commands.suppression.report`.

Example:
    Run the audit over the working tree::

        from rhiza_tools.commands.suppression import suppression_audit_command
        suppression_audit_command(fail_stale_nosec_cve=False, pip_audit_args=[])
"""

from __future__ import annotations

from pathlib import Path

from rhiza_tools.commands.suppression.parse import collect_suppressions
from rhiza_tools.commands.suppression.report import check_stale_nosec_cves, print_report

__all__ = ["suppression_audit_command"]


def suppression_audit_command(fail_stale_nosec_cve: bool, pip_audit_args: list[str]) -> int:
    """Run the suppression audit and print a structured report.

    Scans the working directory tree for inline suppression comments, prints a
    per-file report, a histogram by code, and an overall density grade. When
    ``fail_stale_nosec_cve`` is True it additionally cross-checks CVE-tagged
    ``# nosec`` comments against live pip-audit findings and fails on stale ones.

    Args:
        fail_stale_nosec_cve: If True, fail when ``# nosec`` comments reference
            CVEs that pip-audit no longer reports.
        pip_audit_args: Extra arguments forwarded to pip-audit for the stale-CVE
            gate.

    Returns:
        A process exit code: ``0`` on success, ``1`` when stale CVE-tagged
        ``# nosec`` suppressions are found, or ``2`` when pip-audit fails to run.
    """
    root = Path(".")
    py_files, all_suppressions, total_lines = collect_suppressions(root)
    print_report(py_files, all_suppressions, total_lines)

    if fail_stale_nosec_cve:
        return check_stale_nosec_cves(all_suppressions, pip_audit_args)

    return 0
