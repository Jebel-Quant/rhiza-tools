"""Rhiza Tools — CI helper CLI for the Rhiza ecosystem.

Rhiza Tools is the shared helper CLI for Rhiza-managed projects. Its former
commands have moved elsewhere in the ecosystem, so it currently exposes no
subcommands.

## Usage

```bash
rhiza-tools --version
rhiza-tools --help
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
