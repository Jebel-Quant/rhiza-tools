"""Rhiza Tools — Extra utilities and tools for the Rhiza ecosystem.

Rhiza Tools provides headless CI/CD commands and utilities for the Rhiza
ecosystem: the CI version matrix, coverage badge generation, benchmark
analysis, dependency/suppression auditing, and documentation maintenance.

## Key features

- **CI Version Matrix**: Emit supported Python versions from `pyproject.toml`.
- **Coverage Badges**: Generate a shields.io coverage badge from a coverage report.
- **Security Auditing**: Tiered `pip-audit` and suppression-density reporting.
- **Documentation Helpers**: Keep your README up-to-date with CLI help output.
- **Standalone CLI**: Run directly via `uvx rhiza-tools` — invoked by the Rhiza
  Makefile targets and CI.

## Quick start

Emit the CI version matrix:

```bash
rhiza-tools version-matrix
```

Generate a coverage badge:

```bash
rhiza-tools generate-coverage-badge
```

## Main modules

- `rhiza_tools.cli` — The main Typer application and command definitions.

## Documentation

For more details, see the [README.md](https://github.com/Jebel-Quant/rhiza-tools/blob/main/README.md).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("rhiza-tools")
except PackageNotFoundError:
    # Package is not installed, use a fallback or leave undefined
    __version__ = "unknown"
