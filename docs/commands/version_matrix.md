# Version Matrix

Emit supported Python versions from `pyproject.toml` as JSON.

## Overview

The `version-matrix` command reads the `requires-python` field from
`pyproject.toml` and outputs a JSON array of Python versions that satisfy the
constraint. This is primarily used in GitHub Actions to compute the test matrix
dynamically.

## Usage

```bash
# Get supported versions with defaults
rhiza-tools version-matrix
# Output: ["3.11", "3.12", "3.13"]

# Use custom pyproject.toml path
rhiza-tools version-matrix --pyproject /path/to/pyproject.toml

# Use custom candidate versions
rhiza-tools version-matrix --candidates "3.10,3.11,3.12"
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--pyproject` | `pyproject.toml` | Path to the `pyproject.toml` file |
| `--candidates` | `3.11,3.12,3.13,3.14` | Comma-separated list of candidate Python versions |

## GitHub Actions Example

Use the command in a workflow to build a dynamic test matrix:

```yaml
jobs:
  matrix:
    runs-on: ubuntu-latest
    outputs:
      versions: ${{ steps.matrix.outputs.versions }}
    steps:
      - uses: actions/checkout@v4
      - id: matrix
        run: echo "versions=$(rhiza-tools version-matrix)" >> "$GITHUB_OUTPUT"

  test:
    needs: matrix
    strategy:
      matrix:
        python-version: ${{ fromJson(needs.matrix.outputs.versions) }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: make test
```
