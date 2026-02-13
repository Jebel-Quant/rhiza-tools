# Generate Coverage Badge

Generate a shields.io endpoint badge JSON from a coverage report.

## Overview

The `generate-coverage-badge` command reads a `coverage.json` file produced by
[pytest-cov](https://pytest-cov.readthedocs.io/) and creates a
[shields.io endpoint](https://shields.io/endpoint) JSON file for displaying a
coverage badge. The badge colour automatically adjusts based on the coverage
percentage.

## Usage

```bash
# Generate badge with default paths
rhiza-tools generate-coverage-badge

# Generate badge with custom paths
rhiza-tools generate-coverage-badge \
    --coverage-json tests/coverage.json \
    --output assets/badge.json
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--coverage-json` | `_tests/coverage.json` | Path to the coverage JSON file |
| `--output` | `_book/tests/coverage-badge.json` | Path to write the badge JSON |

## Colour Thresholds

| Coverage | Colour |
|----------|--------|
| ≥ 90% | `brightgreen` |
| ≥ 80% | `green` |
| ≥ 70% | `yellowgreen` |
| ≥ 60% | `yellow` |
| ≥ 50% | `orange` |
| < 50% | `red` |

## Output Format

The generated JSON follows the shields.io endpoint schema:

```json
{
  "schemaVersion": 1,
  "label": "coverage",
  "message": "95%",
  "color": "brightgreen"
}
```

## Generating Coverage Data

Run pytest with coverage to create the input file:

```bash
pytest --cov --cov-report=json:_tests/coverage.json
```
