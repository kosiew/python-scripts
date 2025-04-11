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
import subprocess
import sys

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


def collect_benchmark_results(benchmark_dirs, threshold, p_value_threshold):
    """Collect and filter benchmark results that meet significance criteria."""
    results = []

    for benchmark_dir in benchmark_dirs:
        print(f"\n==> Processing benchmark: {benchmark_dir.name}")
        data = parse_benchmark_report(benchmark_dir)
        if not data:
            print(f"==> No data found for {benchmark_dir.name}")
            continue

        change_data = get_benchmark_change(data)
        if not change_data:
            print(f"==> No valid change data for {benchmark_dir.name}")
            continue

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
            print(f"==> INCLUDED: Benchmark '{benchmark_dir.name}' meets criteria")

            result = (
                benchmark_dir.name,
                change_data["mean_pct"],
                change_data["mean_p_value"],
                change_data["median_pct"],
            )
            results.append(result)
        else:
            print(
                f"==> EXCLUDED: Benchmark '{benchmark_dir.name}' doesn't meet criteria"
            )

    return results


def build_results_table(results, detailed=False):
    """Build a table from benchmark results."""
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

    return table


def save_results_to_file(results, output_file, p_value_threshold):
    """Save benchmark results to a file."""
    improvements = sum(1 for r in results if r[1] < 0)
    regressions = sum(1 for r in results if r[1] > 0)

    with open(output_file, "w") as f:
        f.write(
            f"Criterion Benchmark Summary (Statistically Significant Changes p < {p_value_threshold})\n\n"
        )
        for result in results:
            benchmark_name = result[0]
            mean_pct = result[1]
            p_value = result[2]
            sign = "-" if mean_pct < 0 else "+"
            f.write(f"{benchmark_name}: {sign}{abs(mean_pct):.2f}% (p={p_value:.6f})\n")
        f.write(f"\nSummary: {improvements} improvements, {regressions} regressions\n")

    console.print(f"Results saved to {output_file}")


def get_summary_stats(results):
    """Calculate summary statistics from results."""
    improvements = sum(1 for r in results if r[1] < 0)
    regressions = sum(1 for r in results if r[1] > 0)
    return improvements, regressions


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

    # Find all benchmark directories
    benchmark_dirs = [
        d for d in criterion_dir.iterdir() if d.is_dir() and d.name != "report"
    ]

    # Collect and filter benchmark results
    results = collect_benchmark_results(benchmark_dirs, threshold, p_value_threshold)

    # Sort results by benchmark name
    results.sort(key=lambda x: x[0])

    # Build and display results table
    table = build_results_table(results, detailed)
    console.print(table)

    # Display summary statistics
    improvements, regressions = get_summary_stats(results)
    console.print(
        f"\nSummary: {improvements} improvements, {regressions} regressions (p < {p_value_threshold})"
    )

    # Save results to file if requested
    if output_file:
        save_results_to_file(results, output_file, p_value_threshold)


@app.command()
def compare_branches(
    main_branch: str = typer.Argument(..., help="Main branch name"),
    feature_branch: str = typer.Argument(..., help="Feature branch name"),
    bench_name: str = typer.Option(
        "binary_op", "--bench", "-b", help="Benchmark name to run"
    ),
    profile: str = typer.Option(
        "profiling", "--profile", "-p", help="Cargo profile to use"
    ),
    output_file: str = typer.Option(
        "target/criterion/report/critcmp.txt",
        "--output",
        "-o",
        help="Output file for the comparison report",
    ),
):
    """
    Compare benchmark results between two git branches.

    This command:
    1. Checks out the main branch and runs benchmarks
    2. Checks out the feature branch and runs benchmarks
    3. Compares the results and generates a report
    """
    try:
        # Ensure output directory exists
        prepare_output_directory(output_file)

        # Run benchmarks on both branches
        benchmark_branch(main_branch, bench_name, profile)
        benchmark_branch(feature_branch, bench_name, profile)

        # Compare and report results
        compare_and_report(main_branch, feature_branch, output_file)

    except subprocess.CalledProcessError as e:
        console.print(f"❌ Error executing command: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="bold red")
        sys.exit(1)


def prepare_output_directory(output_file):
    """Ensure the output directory exists."""
    output_dir = os.path.dirname(output_file)
    os.makedirs(output_dir, exist_ok=True)


def benchmark_branch(branch_name, bench_name, profile):
    """Checkout a branch and run benchmarks on it."""
    console.print(
        f"🔁 Checking out {branch_name} and benchmarking...", style="bold blue"
    )
    run_command(["git", "checkout", branch_name])
    run_benchmark(branch_name, bench_name, profile)


def run_benchmark(branch_name, bench_name, profile):
    """Run the benchmark with the specified parameters."""
    run_command(
        [
            "cargo",
            "bench",
            "--bench",
            bench_name,
            f"--profile={profile}",
            "--",
            f"--save-baseline",
            branch_name,
        ]
    )


def compare_and_report(main_branch, feature_branch, output_file):
    """Compare benchmarks and generate a report."""
    console.print(
        f"📊 Comparing benchmarks: {main_branch} vs {feature_branch}",
        style="bold green",
    )
    comparison_result = run_command_with_output(
        ["critcmp", main_branch, feature_branch]
    )

    # Save output to file
    with open(output_file, "w") as f:
        f.write(comparison_result)

    # Display the result with color highlighting
    highlight_comparison_result(comparison_result)

    console.print(f"✅ Report saved to: {output_file}", style="bold green")


def run_command(command):
    """Run a shell command and exit on failure."""
    subprocess.run(command, check=True)


def run_command_with_output(command):
    """Run a shell command and return its output as string."""
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return result.stdout


def highlight_comparison_result(text):
    """Highlight improvements and regressions in the comparison result."""
    lines = text.split("\n")
    for line in lines:
        if "inst/s" in line and ":" in line:
            parts = line.split(":")
            benchmark_name = parts[0].strip()
            stats = parts[1].strip()

            if "-" in stats and not stats.startswith("-"):  # Improvement
                rprint(f"[cyan]{benchmark_name}:[/cyan] [green]{stats}[/green]")
            elif "+" in stats:  # Regression
                rprint(f"[cyan]{benchmark_name}:[/cyan] [red]{stats}[/red]")
            else:
                rprint(f"[cyan]{benchmark_name}:[/cyan] {stats}")
        else:
            print(line)


if __name__ == "__main__":
    app()
