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
        if (current / "src" / "lib.rs").exists():
            crate_name = find_crate_name(current)
            if crate_name:
                return crate_name, current
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
            exports.append((str(filepath.relative_to(root_dir)), f"{m.group(1)}::{m.group(2)}"))
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
        for dep in deps[:3]:
            typer.echo(f"use {normalize_crate_name(dep)}::{struct_name};")
        return None

    typer.echo(f"✅ Found `{struct_name}` in:")
    for f in struct_files:
        typer.echo(f"   - {f.relative_to(workspace_root) if workspace_root else f}")

    statements: list[tuple[str, str]] = []
    for f in struct_files:
        crate, crate_root = find_containing_crate(f)
        if not crate:
            continue
        rel = f.relative_to(crate_root)
        parts = [p for p in rel.with_suffix('').parts if p != 'src' and p != 'mod']
        module = '::'.join(parts)
        if current_crate and current_crate != crate:
            norm = normalize_crate_name(crate)
            statements.append((f"use {norm}::{module + '::' if module else ''}{struct_name};", "direct (from another crate)"))
        else:
            statements.append((f"use crate::{module + '::' if module else ''}{struct_name};", "direct (same crate)"))
    for rel, full in re_exports:
        path = rel
        if full.startswith("crate::"):
            statements.append((f"use crate::{struct_name};", f"re-exported via {path}"))
        else:
            statements.append((f"use {full};", f"re-exported via {path}"))
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
    print(f"==> craft_test called with file_path={file_path}")
    """
    Craft a `cargo test -p <package> --test <testfile>` command to run tests in the specified Rust source file.
    It scans the entire `tests/` directory for `mod <module>;` declarations.
    """
    cwd = Path(os.getcwd())
    print(f"==> cwd={cwd}")
    ws = find_workspace_root(cwd) or cwd
    print(f"==> workspace root={ws}")
    try:
        rel_to_ws = file_path.resolve().relative_to(ws)
        print(f"==> rel_to_ws={rel_to_ws}")
    except ValueError:
        print(f"==> file {file_path} is not inside workspace {ws}")
        typer.echo("❌ The file is not inside the workspace")
        raise typer.Exit(1)

    # Determine crate
    crate_name, crate_root = find_containing_crate(file_path)
    print(f"==> crate_name={crate_name}, crate_root={crate_root}")
    if not crate_name or not crate_root:
        print(f"==> Could not determine crate for {file_path}")
        typer.echo("❌ Could not determine crate for the file")
        raise typer.Exit(1)
    pkg_flag = f"-p {crate_name}"

    # If under tests/
    parts = rel_to_ws.with_suffix('').parts
    print(f"==> rel_to_ws.parts={parts}")
    try:
        idx = parts.index('tests')
        print(f"==> 'tests' found at index {idx}")
    except ValueError:
        idx = -1
        print(f"==> 'tests' not found in parts")

    if idx >= 0:
        module = parts[idx + 1] if len(parts) > idx + 1 else None
        testfile = file_path.stem
        print(f"==> module={module}, testfile={testfile}")
        # scan all tests/*.rs and tests/*/mod.rs for mod declarations
        test_modules = set()
        for rs in (crate_root / 'tests').rglob('*.rs'):
            content = rs.read_text(encoding='utf-8')
            for m in re.finditer(r'mod\s+(\w+)\s*;', content):
                test_modules.add(m.group(1))
        print(f"==> test_modules found: {test_modules}")
        if module and module in test_modules:
            print(f"==> Using module: {module}")
            cmd = f"cargo test {pkg_flag} --test {module}"
        elif testfile in test_modules:
            print(f"==> Using testfile: {testfile}")
            cmd = f"cargo test {pkg_flag} --test {testfile}"
        else:
            print(f"==> Fallback to testfile: {testfile}")
            # fallback to direct file-stem invocation
            cmd = f"cargo test {pkg_flag} --test {testfile}"
    else:
        # unit tests or example
        rel_crate = file_path.resolve().relative_to(crate_root)
        print(f"==> rel_crate (relative to crate_root): {rel_crate}")
        parts2 = [p for p in rel_crate.with_suffix('').parts if p not in ('src', 'mod')]
        print(f"==> parts2 after filtering: {parts2}")
        module_path = '::'.join(parts2)
        print(f"==> module_path: {module_path}")
        cmd = f"cargo test {pkg_flag} {module_path}" if module_path else f"cargo test {pkg_flag}"

    print(f"==> Final test command: {cmd}")
    typer.echo(f"🔧 Test command: {cmd}")


if __name__ == "__main__":
    app()
