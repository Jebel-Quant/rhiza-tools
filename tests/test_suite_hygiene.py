"""Meta-tests that keep the test suite behavior-focused rather than coverage-chasing.

Tests should live with the module they exercise and assert behavior. Files whose
sole purpose is to "hit lines" for a coverage number — a ``test_coverage_*.py``
catch-all bucket, or a module that announces it exists to reach a coverage target —
are disallowed. Coverage honesty is enforced by the mutation-testing job, not by
line-chasing files. (This module names the forbidden wording only to describe the
rule, and excludes itself from the scan.)
"""

from __future__ import annotations

import re
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
_SELF = Path(__file__).name

# Matches purpose statements like "to achieve 100% coverage" / "achieve coverage".
_COVERAGE_CHASING = re.compile(r"achieve[^\n]*coverage", re.IGNORECASE)


def test_no_coverage_bucket_files():
    """There must be no ``test_coverage*.py`` catch-all coverage bucket."""
    offenders = sorted(p.name for p in TESTS_DIR.glob("**/test_coverage*.py"))
    assert not offenders, (
        f"coverage-bucket test files found: {offenders}. Relocate their tests into the test "
        "module for the code they exercise and assert behavior, not line execution."
    )


def test_no_coverage_chasing_docstrings():
    """No test module may declare its purpose as achieving a coverage number."""
    offenders = [
        p.name
        for p in TESTS_DIR.glob("**/test_*.py")
        if p.name != _SELF and _COVERAGE_CHASING.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"coverage-chasing wording found in: {sorted(offenders)}"
