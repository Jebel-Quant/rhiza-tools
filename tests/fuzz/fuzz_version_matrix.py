"""Fuzz the rhiza_tools version-matrix parser against arbitrary strings.

``parse_version`` and ``satisfies`` parse untrusted version and specifier
strings (e.g. from a project's ``pyproject.toml``). They are contracted to
return a result or raise ``VersionSpecifierError`` on malformed input — never to
crash with an unexpected exception. This harness exercises that contract with
coverage-guided input.

Run locally:
    pip install atheris
    python tests/fuzz/fuzz_version_matrix.py -atheris_runs=20000

Run in ClusterFuzzLite: this file is built by .clusterfuzzlite/build.sh.
"""

from __future__ import annotations

import contextlib
import sys

import atheris

with atheris.instrument_imports():
    from rhiza_tools.commands.version_matrix import (
        VersionSpecifierError,
        parse_version,
        satisfies,
    )

# The parsers are documented to raise only VersionSpecifierError on bad input.
# Anything else propagates and is recorded by Atheris as a crash.
_ALLOWED = (VersionSpecifierError,)


def test_one_input(data: bytes) -> None:
    """Parse fuzzed version/specifier strings."""
    fdp = atheris.FuzzedDataProvider(data)
    version = fdp.ConsumeUnicodeNoSurrogates(24)
    specifier = fdp.ConsumeUnicodeNoSurrogates(48)

    with contextlib.suppress(_ALLOWED):
        parse_version(version)
    with contextlib.suppress(_ALLOWED):
        satisfies(version, specifier)


def main() -> None:
    """Run the Atheris fuzz loop."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
