"""Fuzz target for version parsing and specifier evaluation."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

import atheris

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _version_matrix_symbols() -> tuple[type[Exception], object, object]:
    module = import_module("rhiza_tools.commands.version_matrix")
    return module.VersionSpecifierError, module.parse_version, module.satisfies


def test_one_input(data: bytes) -> None:
    """Exercise version parsing and specifier evaluation with fuzzed input."""
    version_specifier_error, parse_version, satisfies = _version_matrix_symbols()
    provider = atheris.FuzzedDataProvider(data)
    version = provider.ConsumeUnicodeNoSurrogates(64)
    specifier = provider.ConsumeUnicodeNoSurrogates(128)

    try:
        parse_version(version)
    except version_specifier_error:
        pass

    try:
        satisfies(version, specifier)
    except version_specifier_error:
        pass


def main() -> None:
    """Run the Atheris fuzz loop for the version matrix target."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
