# API Reference

Full API documentation is generated automatically from source code docstrings
using [pdoc](https://pdoc.dev/).

**[View the full API reference →](https://jebel-quant.github.io/rhiza-tools/pdoc/rhiza_tools.html)**

## Generating API Docs

```bash
make docs
```

This produces HTML documentation in the `_pdoc/` directory.

## Package Structure

```
rhiza_tools/
├── __init__.py          # Package metadata and version
├── __main__.py          # Entry point (Typer app)
├── cli.py               # CLI command definitions
└── commands/
    ├── analyze_benchmarks.py   # Benchmark analysis & visualization
    └── version_matrix.py       # Python version matrix
```

## Key Modules

### `rhiza_tools.cli`

The main Typer application. Defines all CLI commands and their option parsing.

### `rhiza_tools.commands`

Each command module exposes a single `*_command()` function that contains the
core logic, making commands testable independently of the CLI layer.

| Module | Entry Function |
|--------|---------------|
| `analyze_benchmarks` | `analyze_benchmarks_command()` |
| `version_matrix` | `version_matrix_command()` |
