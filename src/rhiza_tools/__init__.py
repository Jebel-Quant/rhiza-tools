"""Rhiza Tools — CI, quality, and security helper CLI for the Rhiza ecosystem.

Rhiza Tools is the shared helper CLI for Rhiza-managed projects. It provides the
CI Python-version matrix, benchmark analysis, and dependency/suppression
auditing.

## Key features

- **Version Matrix**: Emit the supported Python versions for the CI test matrix.
- **Benchmark Analysis**: Summarize and visualize pytest-benchmark results.
- **Dependency & Suppression Auditing**: Tiered `pip-audit` policy and an
  inline-suppression density report.
- **Standalone CLI**: Run directly via `uvx rhiza-tools` — invoked by the Rhiza
  Makefile targets and CI.

## Quick start

Emit the CI Python-version matrix:

```bash
rhiza-tools version-matrix
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
