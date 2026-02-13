# Analyze Benchmarks

Analyze pytest-benchmark results and visualize them.

## Overview

The `analyze-benchmarks` command reads a `benchmarks.json` file produced by
[pytest-benchmark](https://pytest-benchmark.readthedocs.io/), prints a summary
table with benchmark name, mean milliseconds, and operations per second, and
generates an interactive Plotly bar chart of mean runtimes.

!!! note "Extra Dependencies"
    This command requires **pandas** and **plotly**, which are available in the
    `dev` dependency group. Install with:

    ```bash
    uv pip install -e '.[dev]'
    ```

## Usage

```bash
# Analyze benchmarks with default paths
rhiza-tools analyze-benchmarks

# Use custom input and output paths
rhiza-tools analyze-benchmarks \
    --benchmarks-json tests/benchmarks.json \
    --output-html reports/benchmarks.html
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--benchmarks-json` | `_benchmarks/benchmarks.json` | Path to the benchmarks JSON file |
| `--output-html` | `_benchmarks/benchmarks.html` | Path to save the HTML visualization |

## Output

- **Console table** — benchmark name, mean (ms), and ops/sec.
- **HTML file** — interactive Plotly bar chart saved to the output path.

## Generating Benchmark Data

Run your benchmarks with pytest-benchmark to create the input file:

```bash
pytest tests/benchmarks/ --benchmark-json=_benchmarks/benchmarks.json
```
