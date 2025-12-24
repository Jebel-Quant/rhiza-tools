"""Rhiza Tools — Extra utilities and tools for the Rhiza ecosystem.

Rhiza Tools provides additional commands and utilities that extend the capabilities
of the main Rhiza CLI. It includes tools for version management, release automation,
and documentation maintenance.

## Key features

- **Version Bumping**: Automate version updates in `pyproject.toml`.
- **Release Management**: Streamline the release process with git tag automation.
- **Documentation Helpers**: Keep your README up-to-date with CLI help output.
- **Flexible Usage**: Use as a `rhiza` plugin or as a standalone CLI.

## Quick start

Bump the project version:

```bash
rhiza tools bump 1.0.1
# or standalone
rhiza-tools bump 1.0.1
```

Create a release tag:

```bash
rhiza tools release
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
