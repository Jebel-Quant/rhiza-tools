# rhiza-tools

[![PyPI version](https://img.shields.io/pypi/v/rhiza-tools.svg)](https://pypi.org/project/rhiza-tools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Extra utilities and tools serving the mothership [rhiza](https://github.com/Jebel-Quant/rhiza).

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

Bump the version of the project in `pyproject.toml`.

**Usage:**

```bash
# As plugin
rhiza tools bump [VERSION]

# Standalone
rhiza-tools bump [VERSION]
```

**Arguments:**

*   `VERSION` - The version to bump to (e.g., `1.0.1`, `major`, `minor`, `patch`).

**Options:**

*   `--dry-run` - Print what would happen without actually changing files.

### `release`

Create a git tag and push to remote to trigger the release workflow.

**Usage:**

```bash
# As plugin
rhiza tools release

# Standalone
rhiza-tools release
```

**Options:**

*   `--dry-run` - Print what would happen without actually performing git operations.

### `update-readme-help`

Update `README.md` with the current output from `make help`.

**Usage:**

```bash
# As plugin
rhiza tools update-readme-help

# Standalone
rhiza-tools update-readme-help
```

**Options:**

*   `--dry-run` - Print what would happen without actually changing files.

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
