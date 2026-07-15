# <img src="https://raw.githubusercontent.com/Jebel-Quant/rhiza/main/.rhiza/assets/rhiza-logo.svg" alt="Rhiza Logo" width="30" style="vertical-align: middle;"> rhiza-tools
![Synced with Rhiza](https://img.shields.io/badge/synced%20with-rhiza-2FA4A9?color=2FA4A9)

[![PyPI version](https://img.shields.io/pypi/v/rhiza-tools.svg)](https://pypi.org/project/rhiza-tools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://jebel-quant.github.io/rhiza-tools/coverage-badge.svg)](https://jebel-quant.github.io/rhiza-tools/reports/html-coverage/index.html)
[![Downloads](https://static.pepy.tech/personalized-badge/rhiza-tools?period=month&units=international_system&left_color=black&right_color=orange&left_text=PyPI%20downloads%20per%20month)](https://pepy.tech/project/rhiza-tools)
[![CodeFactor](https://www.codefactor.io/repository/github/jebel-quant/rhiza-tools/badge)](https://www.codefactor.io/repository/github/jebel-quant/rhiza-tools)

Extra utilities and tools serving the mothership [rhiza](https://github.com/Jebel-Quant/rhiza).

**📖 New to Rhiza? See the [mothership repository](https://github.com/Jebel-Quant/rhiza) for a beginner-friendly introduction to the ecosystem.**

This package provides additional commands for the Rhiza ecosystem, such as the CI Python-version matrix, benchmark analysis, and dependency/suppression auditing. It is a standalone command-line tool: the Rhiza Makefile targets and CI invoke it via `uvx`, and you can run it directly the same way.

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
