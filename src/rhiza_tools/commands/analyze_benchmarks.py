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
from pathlib import Path
from typing import Any, cast

import typer

from rhiza_tools import console


class BenchmarkError(Exception):
    """Base exception for benchmark analysis errors."""


def _read_benchmarks_data(benchmarks_json: Path) -> object:
    """Read and parse the pytest-benchmark JSON file.

    Args:
        benchmarks_json: Path to the benchmarks.json file.

    Returns:
        The parsed JSON payload.

    Raises:
        typer.Exit: (code 0) if the file is missing or not valid JSON, so the
            command skips gracefully rather than failing CI.
    """
    if not benchmarks_json.exists():
        console.warning(f"benchmarks.json not found at {benchmarks_json}; skipping analysis and exiting successfully.")
        raise typer.Exit()

    try:
        with benchmarks_json.open() as f:
            return json.load(f)
    except json.JSONDecodeError:
        console.warning(
            f"benchmarks.json at {benchmarks_json} is invalid or empty; skipping analysis and exiting successfully."
        )
        raise typer.Exit() from None


def _extract_benchmark_records(data: object, benchmarks_json: Path) -> list[dict[str, Any]]:
    """Validate the benchmark payload and reduce it to plottable records.

    Args:
        data: The parsed benchmarks JSON.
        benchmarks_json: Source path, used only for warning messages.

    Returns:
        A list of ``{Benchmark, Mean_ms, OPS}`` records, one per benchmark.

    Raises:
        typer.Exit: (code 0) if the payload lacks a non-empty ``benchmarks`` list.
    """
    benchmarks = data.get("benchmarks") if isinstance(data, dict) else None
    if not isinstance(benchmarks, list):
        console.warning(
            f"benchmarks.json at {benchmarks_json} missing valid 'benchmarks' list; "
            "skipping analysis and exiting successfully."
        )
        raise typer.Exit()

    if not benchmarks:
        console.warning(
            f"benchmarks.json at {benchmarks_json} contains no benchmarks; skipping analysis and exiting successfully."
        )
        raise typer.Exit()

    return [
        {
            "Benchmark": bench["name"],
            "Mean_ms": bench["stats"]["mean"] * 1000,  # convert seconds → milliseconds
            "OPS": 1 / bench["stats"]["mean"],
        }
        for bench in cast("list[dict[str, Any]]", benchmarks)
    ]


def _render_benchmark_chart(px: Any, df: Any, output_html: Path, show: bool) -> None:
    """Build the Plotly bar chart, save it to HTML, and optionally open it.

    Args:
        px: The imported ``plotly.express`` module.
        df: The (sorted) benchmark DataFrame.
        output_html: Path where the HTML visualization is written.
        show: If True, open the chart in a browser after saving.
    """
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
    console.success(f"Visualization saved to {output_html}")

    # Optionally open the interactive plot in a browser
    if show:
        fig.show()


def analyze_benchmarks_command(
    benchmarks_json: Path | None = None,
    output_html: Path | None = None,
    show: bool = False,
) -> None:
    """Analyze pytest-benchmark results and visualize them.

    This command reads a benchmarks.json file produced by pytest-benchmark,
    prints a reduced table with benchmark name, mean milliseconds, and operations
    per second, and renders an interactive Plotly bar chart of mean runtimes.

    Args:
        benchmarks_json: Path to the benchmarks.json file. Defaults to _benchmarks/benchmarks.json.
        output_html: Path to save the HTML visualization. Defaults to _benchmarks/benchmarks.html.
        show: If True, open the interactive chart in a browser after saving. Defaults to False.

    Raises:
        typer.Exit: If benchmarks.json is missing, invalid, or has no valid benchmarks.

    Example:
        Analyze benchmarks with default paths::

            analyze_benchmarks_command()

        Use custom paths::

            analyze_benchmarks_command(
                benchmarks_json=Path("tests/benchmarks.json"),
                output_html=Path("reports/benchmarks.html")
            )

        Open the chart in a browser after saving::

            analyze_benchmarks_command(show=True)
    """
    # Import pandas and plotly here to avoid requiring them as hard dependencies
    try:
        import pandas as pd
        import plotly.express as px
    except ImportError:
        console.error(
            "pandas and plotly are required for this command. "
            "Install them with: uv pip install -e '.[dev]' or pip install 'rhiza-tools[dev]'"
        )
        raise typer.Exit(code=1) from None

    # Set default paths
    if benchmarks_json is None:
        benchmarks_json = Path("_benchmarks/benchmarks.json")

    if output_html is None:
        output_html = Path("_benchmarks/benchmarks.html")

    data = _read_benchmarks_data(benchmarks_json)
    records = _extract_benchmark_records(data, benchmarks_json)

    # Create DataFrame and sort fastest → slowest
    df = pd.DataFrame(records)
    df = df.sort_values("Mean_ms")

    # Display reduced table
    console.info("Benchmark Results:")
    print(df[["Benchmark", "Mean_ms", "OPS"]].to_string(index=False, float_format="%.3f"))

    _render_benchmark_chart(px, df, output_html, show)
