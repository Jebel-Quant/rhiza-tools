# <img src="https://raw.githubusercontent.com/Jebel-Quant/rhiza/main/.rhiza/assets/rhiza-logo.svg" alt="Rhiza Logo" width="30" style="vertical-align: middle;"> rhiza-tools
![Synced with Rhiza](https://img.shields.io/badge/synced%20with-rhiza-2FA4A9?color=2FA4A9)

[![PyPI version](https://img.shields.io/pypi/v/rhiza-tools.svg)](https://pypi.org/project/rhiza-tools/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://jebel-quant.github.io/rhiza-tools/coverage-badge.svg)](https://jebel-quant.github.io/rhiza-tools/reports/html-coverage/index.html)
[![Downloads](https://static.pepy.tech/personalized-badge/rhiza-tools?period=month&units=international_system&left_color=black&right_color=orange&left_text=PyPI%20downloads%20per%20month)](https://pepy.tech/project/rhiza-tools)
[![CodeFactor](https://www.codefactor.io/repository/github/jebel-quant/rhiza-tools/badge)](https://www.codefactor.io/repository/github/jebel-quant/rhiza-tools)

The Rhiza ecosystem's shared CI helper CLI, serving the mothership [rhiza](https://github.com/Jebel-Quant/rhiza).

**📖 New to Rhiza? See the [mothership repository](https://github.com/Jebel-Quant/rhiza) for a beginner-friendly introduction to the ecosystem.**

rhiza-tools is the Rhiza ecosystem's shared helper CLI. Its former commands have moved elsewhere in the ecosystem, so it currently exposes no subcommands. It remains a standalone command-line tool published to PyPI.

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

rhiza-tools currently exposes no subcommands; its former commands have moved
elsewhere in the Rhiza ecosystem.

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
