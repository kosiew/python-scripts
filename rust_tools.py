import os
import re
import sys
import json
import subprocess
from pathlib import Path
import typer

app = typer.Typer(help="CLI tool to find Rust imports and generate test commands for a given struct or file")


def find_workspace_root(start_dir: Path) -> Path | None:
    current = start_dir.resolve()
    while current != current.parent:
        cargo_toml = current / "Cargo.toml"
        if cargo_toml.exists():
            content = cargo_toml.read_text(encoding="utf-8")
            if "[workspace]" in content:
                return current
        current = current.parent
    return None


def find_crate_name(directory: Path) -> str | None:
    cargo_path = directory / "Cargo.toml"
    if not cargo_path.exists():
        return None
    content = cargo_path.read_text(encoding="utf-8")
    match = re.search(r"\[package\][^\[]*name\s*=\s*\"([^\"]+)\"", content, re.DOTALL)
    return match.group(1) if match else None


def find_containing_crate(directory: Path) -> tuple[str | None, Path | None]:
    current = directory.resolve()
    while current != current.parent:
        cargo_toml = current / "Cargo.toml"
        if cargo_toml.exists():
            content = cargo_toml.read_text(encoding="utf-8")
            match = re.search(r"\[package\][^\[]*name\s*=\s*\"([^\"]+)\"", content, re.DOTALL)
            if match:
                return match.group(1), current
        src_dir = current / "src"
        if src_dir.exists() and (src_dir / "lib.rs").exists():
            crate = find_crate_name(current)
            if crate:
                return crate, current
        current = current.parent
    return None, None


def find_rust_struct(root_dir: Path, struct_name: str) -> list[Path]:
    matches: list[Path] = []
    for filepath in root_dir.rglob("*.rs"):
        content = filepath.read_text(encoding="utf-8")
        if re.search(rf"pub\s+struct\s+{struct_name}\b", content):
            matches.append(filepath)
    return matches


def find_re_exports(root_dir: Path, struct_name: str) -> list[tuple[str, str]]:
    exports: list[tuple[str, str]] = []
    pattern = re.compile(rf"pub\s+use\s+(.+?)::({struct_name})\s*;")
    for filepath in root_dir.rglob("*.rs"):
        content = filepath.read_text(encoding="utf-8")
        for m in pattern.finditer(content):
            full = f"{m.group(1)}::{m.group(2)}"
            rel = str(filepath.relative_to(root_dir))
            exports.append((rel, full))
    return exports


def normalize_crate_name(name: str) -> str:
    return name.replace('-', '_')


def get_crate_dependencies(directory: Path) -> list[str]:
    cargo_path = directory / "Cargo.toml"
    if not cargo_path.exists():
        return []
    content = cargo_path.read_text(encoding="utf-8")
    deps: list[str] = []
    section = re.search(r"\[dependencies\](.*?)(\[|$)", content, re.DOTALL)
    if section:
        for line in section.group(1).splitlines():
            m = re.match(r"^\s*([\w_-]+)\s*=", line)
            if m:
                deps.append(m.group(1))
    return deps


def find_correct_import(root_dir: Path, struct_name: str, workspace_root: Path | None, current_crate: str | None) -> list[tuple[str, str]] | None:
    struct_files = find_rust_struct(root_dir, struct_name)
    re_exports = find_re_exports(root_dir, struct_name)
    if not struct_files and current_crate:
        deps = get_crate_dependencies(Path(os.getcwd()))
        typer.echo(f"❌ Struct `{struct_name}` not found in workspace")
        sugg = [f"use {normalize_crate_name(d)}::{struct_name};" for d in deps]
        for s in sugg[:3]:
            typer.echo(f"  {s}")
        return None

    typer.echo(f"✅ Found `{struct_name}` in:")
    for f in struct_files:
        path = f.relative_to(workspace_root) if workspace_root else f
        typer.echo(f"   - {path}")

    statements: list[tuple[str, str]] = []
    for f in struct_files:
        crate, crate_root = find_containing_crate(f)
        if not crate:
            continue
        rel = f.relative_to(crate_root)
        parts = rel.with_suffix('').parts
        parts = [p for p in parts if p != 'src']
        if parts and parts[-1] == 'mod':
            parts = parts[:-1]
        module = '::'.join(parts)
        if current_crate and current_crate != crate:
            norm = normalize_crate_name(crate)
            stmt = f"use {norm}::{module + '::' if module else ''}{struct_name};"
            statements.append((stmt, "direct (from another crate)"))
        else:
            stmt = f"use crate::{module + '::' if module else ''}{struct_name};"
            statements.append((stmt, "direct (same crate)"))
    for rel, full in re_exports:
        if full.startswith("crate::"):
            statements.append((f"use crate::{struct_name};", f"re-exported via {rel}"))
        else:
            statements.append((f"use {full};", f"re-exported via {rel}"))
    return statements


@app.command()
def find_rust_imports(struct_name: str):
    """
    Find suggested `use` statements for a given Rust struct name in the current workspace.
    """
    cwd = Path(os.getcwd())
    ws = find_workspace_root(cwd) or cwd
    typer.echo(f"📂 Workspace root: {ws}")
    crate, crate_root = find_containing_crate(cwd)
    if crate:
        typer.echo(f"🦀 Current crate: {crate} ({crate_root.relative_to(ws)})")
    else:
        typer.echo("❌ Could not determine current crate")
    typer.echo(f"🔍 Searching for `{struct_name}`...\n")
    use_statements = find_correct_import(ws, struct_name, ws, crate)
    if use_statements:
        typer.echo("🎯 Suggested `use` statements:")
        for stmt, note in use_statements:
            typer.echo(f"  {stmt}  // {note}")


@app.command()
def craft_test(file_path: Path):
    """
    Craft a `cargo test` command to run tests in the specified Rust source file.
    """
    cwd = Path(os.getcwd())
    ws = find_workspace_root(cwd) or cwd
    try:
        rel_to_ws = file_path.resolve().relative_to(ws)
    except ValueError:
        typer.echo("❌ The file is not inside the workspace")
        raise typer.Exit(1)

    # Integration tests in tests/ directory
    if rel_to_ws.parts and rel_to_ws.parts[0] == "tests":
        test_name = file_path.stem
        cmd = f"cargo test --test {test_name}"
    else:
        # Unit tests in src/; derive module path
        crate, crate_root = find_containing_crate(file_path.parent)
        if not crate_root:
            typer.echo("❌ Could not determine crate root for the file")
            raise typer.Exit(1)
        rel = file_path.resolve().relative_to(crate_root)
        parts = rel.with_suffix('').parts
        if parts and parts[0] == 'src':
            parts = parts[1:]
        if parts and parts[-1] == 'mod':
            parts = parts[:-1]
        module_path = '::'.join(parts)
        if module_path:
            # filter tests by module prefix
            cmd = f"cargo test {module_path}::"
        else:
            cmd = "cargo test"

    typer.echo(f"🔧 Test command: {cmd}")


if __name__ == "__main__":
    app()
