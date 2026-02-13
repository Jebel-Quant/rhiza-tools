<div align="center">

# <img src="https://raw.githubusercontent.com/Jebel-Quant/rhiza/main/.rhiza/assets/rhiza-logo.svg" alt="Rhiza Logo" width="30" style="vertical-align: middle;"> rhiza-tools
![Synced with Rhiza](https://img.shields.io/badge/synced%20with-rhiza-2FA4A9?color=2FA4A9)

[![PyPI version](https://img.shields.io/pypi/v/rhiza-tools.svg)](https://pypi.org/project/rhiza-tools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/endpoint?url=https://jebel-quant.github.io/rhiza-tools/tests/coverage-badge.json)](https://jebel-quant.github.io/rhiza-tools/tests/html-coverage/index.html)
[![Downloads](https://static.pepy.tech/personalized-badge/rhiza-tools?period=month&units=international_system&left_color=black&right_color=orange&left_text=PyPI%20downloads%20per%20month)](https://pepy.tech/project/rhiza-tools)
[![CodeFactor](https://www.codefactor.io/repository/github/jebel-quant/rhiza-tools/badge)](https://www.codefactor.io/repository/github/jebel-quant/rhiza-tools)

Extra utilities and tools serving the mothership [rhiza](https://github.com/Jebel-Quant/rhiza).

**📖 New to Rhiza? Check out the [Getting Started Guide](https://github.com/Jebel-Quant/rhiza-cli/blob/ad816ff3e91a8d6f07fcba979bc64576de3d0116/GETTING_STARTED.md) for a beginner-friendly introduction!**
</div>

This package provides additional commands for the Rhiza ecosystem, such as version bumping, release management, and documentation helpers. It can be used as a plugin for `rhiza-cli` or as a standalone tool.

## Installation

### As a Rhiza Plugin (Recommended)

You can install `rhiza-tools` alongside `rhiza-cli` using `uvx` or `pip`. This automatically registers the tools as subcommands under `rhiza tools`.

#### Using uvx (run without installation)

```bash
uvx "rhiza[tools]" tools --help
```

#### Using pip

```bash
pip install "rhiza[tools]"
```

### Standalone Usage

You can also use `rhiza-tools` independently if you don't need the full `rhiza` CLI.

#### Using uvx

```bash
uvx rhiza-tools --help
```

#### Using pip

```bash
pip install rhiza-tools
```

## Commands

### `bump`

Bump the version of the project in `pyproject.toml` using semantic versioning.
Supports interactive selection, explicit version targets, and prerelease types.

**Usage:**

```bash
# Interactive (prompts for bump type)
rhiza-tools bump

# Explicit bump type
rhiza-tools bump patch
rhiza-tools bump minor
rhiza-tools bump major

# Explicit version
rhiza-tools bump 2.0.0

# Prerelease types
rhiza-tools bump alpha
rhiza-tools bump beta
rhiza-tools bump rc
```

**Arguments:**

*   `VERSION` - The version to bump to. Can be an explicit version (e.g., `1.0.1`),
    a bump type (`patch`, `minor`, `major`), a prerelease type (`alpha`, `beta`, `rc`, `dev`),
    or omitted for interactive selection.

**Options:**

*   `--dry-run` - Show what would change without actually modifying files.
*   `--commit` - Automatically commit the version change to git.
*   `--push` - Push changes to remote after commit (implies `--commit`).
*   `--branch BRANCH` - Branch to perform the bump on (switches back after).
*   `--allow-dirty` - Allow bumping even with uncommitted changes.
*   `--verbose`, `-v` - Show detailed output from bump-my-version.

### `release`

Push a release tag to remote to trigger the automated release workflow.
Optionally bumps the version before releasing.

**Usage:**

```bash
# Interactive (prompts for bump and push)
rhiza-tools release

# Dry-run preview
rhiza-tools release --dry-run

# Bump and release in one step
rhiza-tools release --bump MINOR --push

# Interactive bump selection with dry-run preview
rhiza-tools release --with-bump --push --dry-run

# Non-interactive (for CI/CD)
rhiza-tools release --bump PATCH --push --non-interactive
```

**Options:**

*   `--bump TYPE` - Bump type (`MAJOR`, `MINOR`, `PATCH`) to apply before release.
*   `--with-bump` - Interactively select bump type before release (works with `--dry-run`).
*   `--push` - Push changes to remote (default: prompt in interactive mode).
*   `--dry-run` - Show what would happen without making any changes.
*   `--non-interactive`, `-y` - Skip all confirmation prompts (for CI/CD).

### `update-readme`

Update `README.md` with the current output from `make help`.

**Usage:**

```bash
# As plugin
rhiza tools update-readme

# Standalone
rhiza-tools update-readme
```

**Options:**

*   `--dry-run` - Print what would happen without actually changing files.

### `generate-coverage-badge`

Generate a coverage badge JSON file from a pytest-cov coverage report.
The badge color adjusts automatically based on the coverage percentage.

**Usage:**

```bash
# Default paths
rhiza-tools generate-coverage-badge

# Custom paths
rhiza-tools generate-coverage-badge \
    --coverage-json tests/coverage.json \
    --output assets/badge.json
```

**Options:**

*   `--coverage-json PATH` - Path to the coverage.json file (default: `_tests/coverage.json`).
*   `--output PATH` - Path to output badge JSON (default: `_book/tests/coverage-badge.json`).

### `version-matrix`

Emit supported Python versions from `pyproject.toml` as a JSON array.
Primarily used in GitHub Actions to compute the CI test matrix.

**Usage:**

```bash
# Default candidates
rhiza-tools version-matrix

# Custom pyproject path
rhiza-tools version-matrix --pyproject /path/to/pyproject.toml

# Custom candidate versions
rhiza-tools version-matrix --candidates "3.10,3.11,3.12"
```

**Options:**

*   `--pyproject PATH` - Path to pyproject.toml (default: `pyproject.toml`).
*   `--candidates TEXT` - Comma-separated list of candidate Python versions (default: `3.11,3.12,3.13,3.14`).

### `analyze-benchmarks`

Analyze pytest-benchmark results and generate an interactive HTML visualization.
Prints a table of benchmark names, mean runtimes, and operations per second.

**Usage:**

```bash
# Default paths
rhiza-tools analyze-benchmarks

# Custom paths
rhiza-tools analyze-benchmarks \
    --benchmarks-json tests/benchmarks.json \
    --output-html reports/benchmarks.html
```

**Options:**

*   `--benchmarks-json PATH` - Path to benchmarks.json file (default: `_benchmarks/benchmarks.json`).
*   `--output-html PATH` - Path to save HTML visualization (default: `_benchmarks/benchmarks.html`).

## Development

### Prerequisites

*   Python 3.11 or higher
*   `uv` package manager (recommended) or `pip`
*   Git

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/Jebel-Quant/rhiza-tools.git
cd rhiza-tools

# Install dependencies
make install

# Run tests
make test
```

## License

This project is licensed under the MIT License.
