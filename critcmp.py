#!/usr/bin/env python3

import os
import json
import typer
from typing import Optional, List
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

app = typer.Typer()
console = Console()

# Constants
DEFAULT_CRITERION_DIR = Path.home() / ".cargo" / "target" / "criterion"


def find_criterion_dir() -> Path:
    """Locate the criterion directory in the user's cargo target directory."""
    if DEFAULT_CRITERION_DIR.exists():
        return DEFAULT_CRITERION_DIR
    raise FileNotFoundError(
        "Could not find criterion directory. Please specify path explicitly."
    )


def parse_estimates_json(benchmark_dir: Path) -> dict:
    """Parse the estimates.json file for a benchmark to extract performance data."""
    change_file = benchmark_dir / "change" / "estimates.json"
    if not change_file.exists():
        return None

    with open(change_file, "r") as f:
        data = json.load(f)
    return data


def get_benchmark_change(data: dict) -> dict:
    """Extract the relevant change metrics from the estimates data."""
    if not data or "mean" not in data:
        return None

    result = {
        "mean_change": data["mean"]["point_estimate"],
        "mean_pct": data["mean"]["point_estimate"] * 100,
        "median_change": data["median"]["point_estimate"],
        "median_pct": data["median"]["point_estimate"] * 100,
    }
    return result


def get_default_criterion_dir() -> Path:
    """Return the default Criterion directory path."""
    return DEFAULT_CRITERION_DIR


def get_default_output_file(criterion_dir: Path = None) -> str:
    """Return the default output file path in the report folder."""
    if criterion_dir is None:
        criterion_dir = get_default_criterion_dir()
    report_dir = criterion_dir / "report"
    if not report_dir.exists():
        report_dir.mkdir(exist_ok=True)
    return str(report_dir / "summary_critcmp.txt")


def format_percentage(value: float) -> str:
    """Format a number as a percentage string with +/- sign."""
    if value < 0:
        return f"[green]-{abs(value):.2f}%[/green]"  # Improvement (negative is good)
    else:
        return f"[red]+{value:.2f}%[/red]"  # Regression


@app.command()
def analyze(
    criterion_dir: Path = typer.Option(
        get_default_criterion_dir(),
        "--dir",
        "-d",
        help="Path to the criterion directory",
        exists=True,
        dir_okay=True,
        file_okay=False,
    ),
    threshold: float = typer.Option(
        1.0, "--threshold", "-t", help="Threshold percentage for significant changes"
    ),
    output_file: str = typer.Option(
        None,  # None here to allow dynamic default based on criterion_dir
        "--output",
        "-o",
        help="Output file for the summary (defaults to <criterion_dir>/report/summary_critcmp.txt)",
    ),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed metrics"),
):
    """Analyze Criterion benchmark results and summarize improvements and regressions."""
    # Set default output file if not specified
    if output_file is None:
        output_file = get_default_output_file(criterion_dir)

    # Create table for results
    table = Table(title="Criterion Benchmark Summary")
    table.add_column("Benchmark", style="cyan")
    table.add_column("Mean Change", justify="right")

    if detailed:
        table.add_column("Median Change", justify="right")

    # Find all benchmark directories
    benchmark_dirs = [
        d for d in criterion_dir.iterdir() if d.is_dir() and d.name != "report"
    ]

    results = []
    for benchmark_dir in benchmark_dirs:
        data = parse_estimates_json(benchmark_dir)
        if data:
            change_data = get_benchmark_change(data)
            if change_data:
                # Only include changes above the threshold
                if abs(change_data["mean_pct"]) >= threshold:
                    benchmark_name = benchmark_dir.name
                    mean_formatted = format_percentage(change_data["mean_pct"])

                    if detailed:
                        median_formatted = format_percentage(change_data["median_pct"])
                        table.add_row(benchmark_name, mean_formatted, median_formatted)
                        results.append(
                            (
                                benchmark_name,
                                change_data["mean_pct"],
                                change_data["median_pct"],
                            )
                        )
                    else:
                        table.add_row(benchmark_name, mean_formatted)
                        results.append((benchmark_name, change_data["mean_pct"]))

    # Display results
    console.print(table)

    # Summary statistics
    improvements = sum(1 for r in results if r[1] < 0)
    regressions = sum(1 for r in results if r[1] > 0)

    console.print(f"\nSummary: {improvements} improvements, {regressions} regressions")

    # Save to file if requested
    if output_file:
        with open(output_file, "w") as f:
            f.write(f"Criterion Benchmark Summary\n\n")
            for result in results:
                benchmark_name = result[0]
                mean_pct = result[1]
                sign = "-" if mean_pct < 0 else "+"
                f.write(f"{benchmark_name}: {sign}{abs(mean_pct):.2f}%\n")
            f.write(
                f"\nSummary: {improvements} improvements, {regressions} regressions\n"
            )
        console.print(f"Results saved to {output_file}")


if __name__ == "__main__":
    app()
