"""Fuzz the suppression comment matcher against arbitrary strings.

``_match_suppression`` parses untrusted comment text (harvested from scanned
source files) against the ``# noqa`` / ``# nosec`` / ``# type: ignore`` /
``# pragma: no cover`` / ``# noinspection`` patterns, and ``nosec_cves``
extracts CVE identifiers from the matches. Both are contracted to return a
value — never to crash on arbitrary input. This harness exercises that contract
with coverage-guided input.

Run locally:
    pip install atheris
    python tests/fuzz/fuzz_suppression.py -atheris_runs=20000

Run in ClusterFuzzLite: this file is built by .clusterfuzzlite/build.sh.
"""

from __future__ import annotations

import sys
from pathlib import Path

import atheris

with atheris.instrument_imports():
    from rhiza_tools.commands.suppression.parse import _match_suppression, nosec_cves


def test_one_input(data: bytes) -> None:
    """Match a fuzzed comment token, then extract CVEs from any result."""
    fdp = atheris.FuzzedDataProvider(data)
    tok_string = fdp.ConsumeUnicodeNoSurrogates(256)
    line_no = fdp.ConsumeIntInRange(1, 1_000_000)

    # Contract: returns a Suppression or None, never raises on arbitrary text.
    suppression = _match_suppression(tok_string, line_no, Path("fuzz_input.py"))
    if suppression is not None:
        # Chain into the CVE extractor so its regex is fuzzed on real matches.
        nosec_cves([suppression])


def main() -> None:
    """Run the Atheris fuzz loop."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
