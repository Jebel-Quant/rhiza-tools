"""Fuzz target for version parsing and specifier evaluation."""

from __future__ import annotations

import sys
from pathlib import Path

import atheris

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rhiza_tools.commands.version_matrix import VersionSpecifierError, parse_version, satisfies


def test_one_input(data: bytes) -> None:
    provider = atheris.FuzzedDataProvider(data)
    version = provider.ConsumeUnicodeNoSurrogates(64)
    specifier = provider.ConsumeUnicodeNoSurrogates(128)

    try:
        parse_version(version)
    except VersionSpecifierError:
        pass

    try:
        satisfies(version, specifier)
    except VersionSpecifierError:
        pass


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
