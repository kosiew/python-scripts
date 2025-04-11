#!/usr/bin/env python3

import os
import json
from bs4 import BeautifulSoup
import re
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


def parse_benchmark_report(benchmark_dir: Path) -> dict:
    """Parse the index.html report file for a benchmark to extract performance data."""
    report_file = benchmark_dir / "report" / "index.html"
    print(f"==> Checking for file: {report_file}")
    if not report_file.exists():
        print(f"==> File does not exist: {report_file}")
        return None

    try:
        soup = load_html_file(report_file)
        if not soup:
            return None

        print(f"==> Successfully parsed HTML for {benchmark_dir.name}")

        # Extract performance data from the HTML
        data = extract_performance_data(soup)
        print(f"==> Extracted data: {data}")
        return data

    except Exception as e:
        print(f"==> Error parsing report: {e}")
        import traceback

        print(traceback.format_exc())
        return None


def load_html_file(file_path: Path):
    """Load and parse an HTML file."""
    try:
        with open(file_path, "r") as f:
            html_content = f.read()
        return BeautifulSoup(html_content, "html.parser")
    except Exception as e:
        print(f"==> Error loading HTML file: {e}")
        return None


def extract_performance_data(soup) -> dict:
    """Extract performance data from the HTML soup object."""
    data = {}

    # Find tables that contain performance data
    tables = soup.find_all("table")
    print(f"==> Found {len(tables)} tables in the report")

    for table in tables:
        process_table(table, data)

    # If we found mean data, add a placeholder for median with the same values
    # This is a simplification since the HTML example only showed one row
    if "mean" in data and "median" not in data:
        data["median"] = data["mean"].copy()

    return data


def process_table(table, data: dict):
    """Process a table to find and extract change data."""
    # Find rows that contain "Change in time"
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if not cells or len(cells) == 0:
            continue

        if "Change in time" in cells[0].text:
            print(f"==> Found 'Change in time' row")
            extract_change_data_from_row(cells, data)


def extract_change_data_from_row(cells, data: dict):
    """Extract change percentage and p-value from a row cells."""
    # The percentage change is in the middle column (index 2)
    if len(cells) > 2:
        percentage = extract_percentage_change(cells[2].text.strip())
        if percentage is not None:
            if "mean" not in data:
                data["mean"] = {}
            data["mean"]["point_estimate"] = percentage / 100

    # The p-value is in the last column
    if len(cells) > 4:
        p_value = extract_p_value(cells[4].text.strip())
        if p_value is not None:
            if "mean" not in data:
                data["mean"] = {}
            data["mean"]["p_value"] = p_value


def extract_percentage_change(text: str) -> float:
    """Extract percentage change from text."""
    change_match = re.search(r"([+-]?\d+\.\d+)%", text)
    if change_match:
        percentage = float(change_match.group(1))
        print(f"==> Found percentage change: {percentage}%")
        return percentage
    return None


def extract_p_value(text: str) -> float:
    """Extract p-value from text."""
    p_value_match = re.search(r"p\s*=\s*(\d+\.\d+)", text)
    if not p_value_match:  # Try another format for p = 0.00 < 0.05
        p_value_match = re.search(r"p\s*=\s*(\d+\.\d+)\s*[<>=]", text)

    if p_value_match:
        p_value = float(p_value_match.group(1))
        print(f"==> Found p-value: {p_value}")
        return p_value
    return None


def get_benchmark_change(data: dict) -> dict:
    """Extract the relevant change metrics from the estimates data."""
    if not data or "mean" not in data:
        print(f"==> Invalid data format in get_benchmark_change")
        return None

    result = {
        "mean_change": data["mean"]["point_estimate"],
        "mean_pct": data["mean"]["point_estimate"] * 100,
        "mean_p_value": data["mean"].get(
            "p_value", 1.0
        ),  # Default to 1.0 if not present
        "median_change": data["median"]["point_estimate"],
        "median_pct": data["median"]["point_estimate"] * 100,
        "median_p_value": data["median"].get(
            "p_value", 1.0
        ),  # Default to 1.0 if not present
    }
    print(
        f"==> Extracted change data: mean_pct={result['mean_pct']:.2f}%, p_value={result['mean_p_value']}"
    )
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
    p_value_threshold: float = typer.Option(
        0.05,
        "--p-value",
        "-p",
        help="P-value threshold for statistical significance (default: 0.05)",
    ),
):
    """Analyze Criterion benchmark results and summarize improvements and regressions.

    This script should be run after executing 'cargo bench' twice:
    1. First run 'cargo bench' for your baseline/current code
    2. Then make your changes and run 'cargo bench' again

    The script will then analyze and summarize the performance differences between
    the baseline and your changes, highlighting improvements and regressions.
    Only statistically significant changes (p < 0.05) are included by default.
    """
    # Set default output file if not specified
    if output_file is None:
        output_file = get_default_output_file(criterion_dir)

    # Create table for results
    table = Table(
        title="Criterion Benchmark Summary (Statistically Significant Changes)"
    )
    table.add_column("Benchmark", style="cyan")
    table.add_column("Mean Change", justify="right")
    table.add_column("P-value", justify="right")

    if detailed:
        table.add_column("Median Change", justify="right")

    # Find all benchmark directories
    benchmark_dirs = [
        d for d in criterion_dir.iterdir() if d.is_dir() and d.name != "report"
    ]

    results = []
    for benchmark_dir in benchmark_dirs:
        print(f"\n==> Processing benchmark: {benchmark_dir.name}")
        data = parse_benchmark_report(benchmark_dir)
        if data:
            change_data = get_benchmark_change(data)
            if change_data:
                print(
                    f"==> Checking threshold: abs({change_data['mean_pct']:.2f}) >= {threshold} = {abs(change_data['mean_pct']) >= threshold}"
                )
                print(
                    f"==> Checking p-value: {change_data['mean_p_value']} < {p_value_threshold} = {change_data['mean_p_value'] < p_value_threshold}"
                )

                # Only include changes above threshold AND statistically significant
                if (
                    abs(change_data["mean_pct"]) >= threshold
                    and change_data["mean_p_value"] < p_value_threshold
                ):
                    print(
                        f"==> INCLUDED: Benchmark '{benchmark_dir.name}' meets criteria"
                    )
                    benchmark_name = benchmark_dir.name
                    mean_formatted = format_percentage(change_data["mean_pct"])
                    p_value = f"{change_data['mean_p_value']:.6f}"

                    if detailed:
                        median_formatted = format_percentage(change_data["median_pct"])
                        table.add_row(
                            benchmark_name, mean_formatted, p_value, median_formatted
                        )
                        results.append(
                            (
                                benchmark_name,
                                change_data["mean_pct"],
                                change_data["mean_p_value"],
                                change_data["median_pct"],
                            )
                        )
                    else:
                        table.add_row(benchmark_name, mean_formatted, p_value)
                        results.append(
                            (
                                benchmark_name,
                                change_data["mean_pct"],
                                change_data["mean_p_value"],
                            )
                        )
                else:
                    print(
                        f"==> EXCLUDED: Benchmark '{benchmark_dir.name}' doesn't meet criteria"
                    )
            else:
                print(f"==> No valid change data for {benchmark_dir.name}")
        else:
            print(f"==> No data found for {benchmark_dir.name}")

    # Sort results by benchmark name
    results.sort(key=lambda x: x[0])

    # Rebuild the table with sorted results
    table = Table(
        title="Criterion Benchmark Summary (Statistically Significant Changes)"
    )
    table.add_column("Benchmark", style="cyan")
    table.add_column("Mean Change", justify="right")
    table.add_column("P-value", justify="right")

    if detailed:
        table.add_column("Median Change", justify="right")

    for result in results:
        benchmark_name = result[0]
        mean_pct = result[1]
        p_value = f"{result[2]:.6f}"
        mean_formatted = format_percentage(mean_pct)

        if detailed and len(result) > 3:
            median_formatted = format_percentage(result[3])
            table.add_row(benchmark_name, mean_formatted, p_value, median_formatted)
        else:
            table.add_row(benchmark_name, mean_formatted, p_value)

    # Display results
    console.print(table)

    # Summary statistics
    improvements = sum(1 for r in results if r[1] < 0)
    regressions = sum(1 for r in results if r[1] > 0)

    console.print(
        f"\nSummary: {improvements} improvements, {regressions} regressions (p < {p_value_threshold})"
    )

    # Save to file if requested
    if output_file:
        with open(output_file, "w") as f:
            f.write(
                f"Criterion Benchmark Summary (Statistically Significant Changes p < {p_value_threshold})\n\n"
            )
            for result in results:
                benchmark_name = result[0]
                mean_pct = result[1]
                p_value = result[2]
                sign = "-" if mean_pct < 0 else "+"
                f.write(
                    f"{benchmark_name}: {sign}{abs(mean_pct):.2f}% (p={p_value:.6f})\n"
                )
            f.write(
                f"\nSummary: {improvements} improvements, {regressions} regressions\n"
            )
        console.print(f"Results saved to {output_file}")


if __name__ == "__main__":
    app()
