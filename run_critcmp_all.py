import os
import subprocess
import typer
from pathlib import Path

app = typer.Typer(help="Batch compare Criterion benchmarks using critcmp.")

@app.command()
def run(
    dir: Path = typer.Option(
        "~/.cargo/target/criterion",
        help="Path to the Criterion benchmarks directory.",
        show_default=True
    ),
    skip_report: bool = typer.Option(
        True,
        help="Skip 'report' folder.",
    ),
):
    criterion_dir = dir.expanduser()
    if not criterion_dir.exists():
        typer.echo(f"❌ Directory not found: {criterion_dir}")
        raise typer.Exit(code=1)

    typer.echo("🚀 Starting batch critcmp...\n")

    for entry in criterion_dir.iterdir():
        if not entry.is_dir():
            continue
        if skip_report and entry.name == "report":
            continue

        before = entry / "before"
        new = entry / "new"

        if before.is_dir() and new.is_dir():
            typer.echo(f"🔍 Comparing benchmarks in: {entry.name}")
            try:
                subprocess.run(["critcmp", str(before), str(new)], check=True)
            except subprocess.CalledProcessError as e:
                typer.echo(f"⚠️  critcmp failed for {entry.name}: {e}")
        else:
            typer.echo(f"⏭️  Skipping {entry.name} (missing 'before' or 'new')")

    typer.echo("\n✅ Done!")


if __name__ == "__main__":
    app()
