"""Fuzz target for version parsing and specifier evaluation."""

from __future__ import annotations

import sys
from contextlib import suppress

import atheris

# Import statically at module scope so PyInstaller (used by
# compile_python_fuzzer) bundles rhiza_tools into the standalone fuzz target.
# A dynamic importlib.import_module() call is invisible to PyInstaller's static
# analysis and leaves the module out of the binary, which made the target crash
# at startup with ModuleNotFoundError. The package is pip-installed into the
# build image (see .clusterfuzzlite/build.sh), so no sys.path manipulation is
# needed.
from rhiza_tools.commands.version_matrix import (
    VersionSpecifierError,
    parse_version,
    satisfies,
)


def test_one_input(data: bytes) -> None:
    """Exercise version parsing and specifier evaluation with fuzzed input."""
    provider = atheris.FuzzedDataProvider(data)
    version = provider.ConsumeUnicodeNoSurrogates(64)
    specifier = provider.ConsumeUnicodeNoSurrogates(128)

    with suppress(VersionSpecifierError):
        parse_version(version)

    with suppress(VersionSpecifierError):
        satisfies(version, specifier)


def main() -> None:
    """Run the Atheris fuzz loop for the version matrix target."""
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
