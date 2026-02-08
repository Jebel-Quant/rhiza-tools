"""Command to analyze pytest-benchmark results and visualize them.

This module reads a local ``benchmarks.json`` file produced by pytest-benchmark,
prints a reduced table with benchmark name, mean milliseconds, and operations
per second, and renders an interactive Plotly bar chart of mean runtimes.

Note: This command requires pandas and plotly, which are available in the dev
dependency group. Install with: uv pip install -e ".[dev]"

Example:
    Analyze benchmarks with default path::

        from rhiza_tools.commands.analyze_benchmarks import analyze_benchmarks_command
        analyze_benchmarks_command()

    Analyze benchmarks with custom path::

        from pathlib import Path
        analyze_benchmarks_command(benchmarks_json=Path("custom/benchmarks.json"))
"""

# /// script
# dependencies = [
#   "pandas",
#   "plotly",
# ]
# ///

import json
import sys
from pathlib import Path

from loguru import logger


class BenchmarkError(Exception):
    """Base exception for benchmark analysis errors."""


def analyze_benchmarks_command(
    benchmarks_json: Path | None = None,
    output_html: Path | None = None,
) -> None:
    """Analyze pytest-benchmark results and visualize them.

    This command reads a benchmarks.json file produced by pytest-benchmark,
    prints a reduced table with benchmark name, mean milliseconds, and operations
    per second, and renders an interactive Plotly bar chart of mean runtimes.

    Args:
        benchmarks_json: Path to the benchmarks.json file. Defaults to _benchmarks/benchmarks.json.
        output_html: Path to save the HTML visualization. Defaults to _benchmarks/benchmarks.html.

    Raises:
        SystemExit: If benchmarks.json is missing, invalid, or has no valid benchmarks.

    Example:
        Analyze benchmarks with default paths::

            analyze_benchmarks_command()

        Use custom paths::

            analyze_benchmarks_command(
                benchmarks_json=Path("tests/benchmarks.json"),
                output_html=Path("reports/benchmarks.html")
            )
    """
    # Import pandas and plotly here to avoid requiring them as hard dependencies
    try:
        import pandas as pd
        import plotly.express as px
    except ImportError:
        logger.error(
            "pandas and plotly are required for this command. "
            "Install them with: uv pip install -e '.[dev]' or pip install 'rhiza-tools[dev]'"
        )
        sys.exit(1)

    # Set default paths
    if benchmarks_json is None:
        benchmarks_json = Path("_benchmarks/benchmarks.json")

    if output_html is None:
        output_html = Path("_benchmarks/benchmarks.html")

    # Check if the file exists
    if not benchmarks_json.exists():
        logger.warning(f"benchmarks.json not found at {benchmarks_json}; skipping analysis and exiting successfully.")
        sys.exit(0)

    # Load pytest-benchmark JSON
    try:
        with benchmarks_json.open() as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logger.warning(
            f"benchmarks.json at {benchmarks_json} is invalid or empty; skipping analysis and exiting successfully."
        )
        sys.exit(0)

    # Validate structure: require a 'benchmarks' list
    if not isinstance(data, dict) or "benchmarks" not in data or not isinstance(data["benchmarks"], list):
        logger.warning(
            f"benchmarks.json at {benchmarks_json} missing valid 'benchmarks' list; "
            "skipping analysis and exiting successfully."
        )
        sys.exit(0)

    # Check if benchmarks list is empty
    if not data["benchmarks"]:
        logger.warning(
            f"benchmarks.json at {benchmarks_json} contains no benchmarks; skipping analysis and exiting successfully."
        )
        sys.exit(0)

    # Extract relevant info: Benchmark name, Mean (ms), OPS
    benchmarks = []
    for bench in data["benchmarks"]:
        mean_s = bench["stats"]["mean"]
        benchmarks.append(
            {
                "Benchmark": bench["name"],
                "Mean_ms": mean_s * 1000,  # convert seconds → milliseconds
                "OPS": 1 / mean_s,
            }
        )

    # Create DataFrame and sort fastest → slowest
    df = pd.DataFrame(benchmarks)
    df = df.sort_values("Mean_ms")

    # Display reduced table
    logger.info("Benchmark Results:")
    print(df[["Benchmark", "Mean_ms", "OPS"]].to_string(index=False, float_format="%.3f"))

    # Create interactive Plotly bar chart
    fig = px.bar(
        df,
        x="Benchmark",
        y="Mean_ms",
        color="Mean_ms",
        color_continuous_scale="Viridis_r",
        title="Benchmark Mean Runtime (ms) per Test",
        text="Mean_ms",
    )

    fig.update_traces(texttemplate="%{text:.2f} ms", textposition="outside")
    fig.update_layout(
        xaxis_tickangle=-45,
        yaxis_title="Mean Runtime (ms)",
        coloraxis_colorbar={"title": "ms"},
        height=600,
        margin={"t": 100, "b": 200},
    )

    # Create output directory if it doesn't exist
    output_html.parent.mkdir(parents=True, exist_ok=True)

    # Save HTML visualization
    fig.write_html(output_html)
    logger.success(f"Visualization saved to {output_html}")

    # Show interactive plot in browser
    fig.show()
