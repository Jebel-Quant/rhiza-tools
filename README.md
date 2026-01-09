<div align="center">

# <img src="https://raw.githubusercontent.com/Jebel-Quant/rhiza/main/assets/rhiza-logo.svg" alt="Rhiza Logo" width="30" style="vertical-align: middle;"> rhiza-tools

![Synced with Rhiza](https://img.shields.io/badge/synced%20with-rhiza-2FA4A9)
[![PyPI version](https://img.shields.io/pypi/v/rhiza-tools.svg)](https://pypi.org/project/rhiza-tools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/endpoint?url=https://jebel-quant.github.io/rhiza-tools/_book/badges/coverage-badge.json)](https://jebel-quant.github.io/rhiza-tools/_book/badges/html-coverage/index.html)
![Python versions](https://img.shields.io/pypi/pyversions/rhiza-tools.svg)
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

### `generate-badges`

Generate shields.io endpoint badge JSON files for your project. Reads badge configuration from `.rhiza/.cfg.toml`, or specify badges via command line.

**Usage:**

```bash
# As plugin
rhiza tools generate-badges

# Standalone
rhiza-tools generate-badges

# Generate specific badges
rhiza-tools generate-badges --badges coverage,license,pypi-version

# Generate all available badges
rhiza-tools generate-badges --all

# Generate badges and update README
rhiza-tools generate-badges --all --update-readme
```

**Options:**

*   `--badges, -b` - Comma-separated list of badges to generate (e.g., `coverage,license`). If not specified, reads from `.rhiza/.cfg.toml` or defaults to `synced-with-rhiza`.
*   `--output-dir, -o` - Output directory for badge files. Defaults to `_book/badges`.
*   `--all, -a` - Generate all available badges.
*   `--update-readme, -u` - Add or update badge markdown in README.md.
*   `--readme` - Path to README.md file (defaults to `README.md`).
*   `--badge-url-base` - Base URL for hosted badges (e.g., `https://org.github.io/repo/badges`).
*   `--dry-run` - Print what would happen without writing files.

**Example: Generate badges and update README:**

```bash
rhiza-tools generate-badges --all \
  --add-to-readme \
  --badge-url-base https://jebel-quant.github.io/my-project/badges
```

**Available Badge Types:**

| Badge | Description | Output File |
|-------|-------------|-------------|
| `synced-with-rhiza` | Shows project is synced with Rhiza template | `synced-with-rhiza-badge.json` |
| `coverage` | Code coverage percentage (reads from `coverage.json`) | `coverage-badge.json` |
| `pypi-version` | PyPI package version | `pypi-version-badge.json` |
| `license` | Project license | `license-badge.json` |
| `python-versions` | Supported Python versions | `python-versions-badge.json` |
| `downloads` | PyPI download statistics | `downloads-badge.json` |
| `codefactor` | CodeFactor grade | `codefactor-badge.json` |

**Configuration:**

You can configure this command in `.rhiza/.cfg.toml`:

```toml
[tool.generate-badges]
output_dir = "_book/badges"
badges = ["synced-with-rhiza", "coverage", "license"]

[tool.generate-badges.coverage]
coverage_json = "_tests/coverage.json"
badge_filename = "coverage-badge.json"

[tool.generate-badges.coverage.thresholds]
90 = "brightgreen"
80 = "green"
70 = "yellowgreen"
60 = "yellow"
50 = "orange"
0 = "red"
```

**Using the Generated Badges:**

The generated JSON files are compatible with shields.io's [endpoint badge](https://shields.io/badges/endpoint-badge) feature. Host them on GitHub Pages (or any public URL) and reference them in your README:

```markdown
```

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
