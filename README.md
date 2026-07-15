# <img src="https://raw.githubusercontent.com/Jebel-Quant/rhiza/main/.rhiza/assets/rhiza-logo.svg" alt="Rhiza Logo" width="30" style="vertical-align: middle;"> rhiza-tools
![Synced with Rhiza](https://img.shields.io/badge/synced%20with-rhiza-2FA4A9?color=2FA4A9)

[![PyPI version](https://img.shields.io/pypi/v/rhiza-tools.svg)](https://pypi.org/project/rhiza-tools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://jebel-quant.github.io/rhiza-tools/coverage-badge.svg)](https://jebel-quant.github.io/rhiza-tools/reports/html-coverage/index.html)
[![Downloads](https://static.pepy.tech/personalized-badge/rhiza-tools?period=month&units=international_system&left_color=black&right_color=orange&left_text=PyPI%20downloads%20per%20month)](https://pepy.tech/project/rhiza-tools)
[![CodeFactor](https://www.codefactor.io/repository/github/jebel-quant/rhiza-tools/badge)](https://www.codefactor.io/repository/github/jebel-quant/rhiza-tools)

Extra utilities and tools serving the mothership [rhiza](https://github.com/Jebel-Quant/rhiza).

**📖 New to Rhiza? See the [mothership repository](https://github.com/Jebel-Quant/rhiza) for a beginner-friendly introduction to the ecosystem.**

This package provides additional commands for the Rhiza ecosystem, such as version bumping, release management, and documentation helpers. It is a standalone command-line tool: the Rhiza Makefile targets and CI invoke it via `uvx`, and you can run it directly the same way.

## Installation

`rhiza-tools` is published to PyPI and runs as a standalone tool — no `rhiza-cli` install required.

### Using uvx (run without installation)

```bash
uvx rhiza-tools --help
```

### Using pip

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

### `rollback`

Reverse a release and/or version bump. Deletes the release tag locally and on the
remote, and optionally reverts the version-bump commit. Uses `git revert` (not
`git reset`), so it is safe even after the changes have been pushed.

**Usage:**

```bash
# Interactive (choose from recent tags)
rhiza-tools rollback

# Preview a specific tag's rollback
rhiza-tools rollback v1.2.3 --dry-run

# Also revert the version-bump commit, no prompts (for CI/CD)
rhiza-tools rollback v1.2.3 --revert-bump --non-interactive
```

**Options:**

*   `--revert-bump` - Also revert the version-bump commit associated with the tag.
*   `--dry-run` - Show what would happen without making any changes.
*   `--non-interactive`, `-y` - Skip all confirmation prompts (for CI/CD).
*   `--verbose` - Enable verbose debug output.

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

### `pip-audit`

Run `pip-audit` with a tiered vulnerability policy. Vulnerabilities in runtime
dependencies fail the command; findings in build tooling (`pip`, `setuptools`,
`wheel`, `distribute`) warn without failing. Any arguments after the command are
forwarded verbatim to `pip-audit`.

**Usage:**

```bash
# Audit the current environment
rhiza-tools pip-audit

# Forward flags through to pip-audit
rhiza-tools pip-audit --ignore-vuln CVE-2024-1234
```

**Options:**

*   `--verbose`, `-v` - Show verbose debug output.
*   Any other arguments are forwarded to `pip-audit`.

### `suppression-audit`

Scan the codebase for inline suppression comments (`# noqa`, `# nosec`,
`# type: ignore`, `# pragma: no cover`, `# noinspection`) and print a per-file
report, an ASCII histogram, and a suppression-density letter grade.

**Usage:**

```bash
# Report suppressions and grade
rhiza-tools suppression-audit

# Also fail on stale CVE-tagged # nosec comments
rhiza-tools suppression-audit --fail-stale-nosec-cve
```

**Options:**

*   `--fail-stale-nosec-cve` - Fail when `# nosec` comments reference CVEs that
    `pip-audit` no longer reports.
*   `--verbose`, `-v` - Show verbose debug output.
*   Any other arguments are forwarded to `pip-audit` (for the stale-CVE gate).

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

## Community

- [Contributing guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Architecture decisions](docs/development/DECISIONS.md)
- [Testing guide](docs/development/TESTS.md)
- [Release guide](docs/RELEASING.md)

## License

This project is licensed under the MIT License.
