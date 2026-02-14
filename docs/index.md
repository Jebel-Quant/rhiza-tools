# Rhiza Tools Documentation

Extra utilities and tools for the [Rhiza](https://github.com/Jebel-Quant/rhiza) ecosystem.

[![PyPI version](https://img.shields.io/pypi/v/rhiza-tools.svg)](https://pypi.org/project/rhiza-tools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is Rhiza Tools?

`rhiza-tools` provides CLI commands for the Rhiza ecosystem, including version bumping, release management, benchmark analysis, and documentation helpers. It can be used as a plugin for `rhiza-cli` or as a standalone tool.

## Installation

### As a Rhiza Plugin (Recommended)

```bash
uvx "rhiza[tools]" tools --help
```

### Standalone

```bash
pip install rhiza-tools
```

## Commands

| Command                  | Description                                              |
|--------------------------|----------------------------------------------------------|
| [bump](commands/bump.md) | Bump the project version using semantic versioning       |
| [release](commands/release.md) | Push a release tag to trigger the release workflow |
| [update-readme](commands/update_readme.md) | Update README.md with `make help` output |
| [generate-coverage-badge](commands/generate_coverage_badge.md) | Generate a coverage badge JSON file |
| [version-matrix](commands/version_matrix.md) | Emit supported Python versions as JSON |
| [analyze-benchmarks](commands/analyze_benchmarks.md) | Analyze and visualise benchmark results |

## Quick Start

```bash
# Install the project
make install

# Run tests
make test

# Bump version interactively
rhiza-tools bump

# Release
rhiza-tools release --with-bump --push
```

## Further Reading

- [Configuration](configuration.md) — `.rhiza/.cfg.toml` reference and customization
- [Releasing](RELEASING.md) — bump and release workflow with flowcharts
- [API Reference](api_reference.md) — module and function documentation
- [Rhiza Framework Docs](https://github.com/Jebel-Quant/rhiza) — architecture, customization, glossary, and more

