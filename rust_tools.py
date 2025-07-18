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
def _get_workspace_and_relative_path(file_path: Path) -> tuple[Path, Path]:
    """Return workspace root and file path relative to workspace, or exit if not inside workspace."""
    cwd = Path(os.getcwd())
    print(f"==> Current working directory: {cwd}")
    ws = find_workspace_root(cwd) or cwd
    print(f"==> Workspace root: {ws}")
    try:
        rel_to_ws = file_path.resolve().relative_to(ws)
        print(f"==> File relative to workspace: {rel_to_ws}")
    except ValueError:
        print(f"==> ERROR: The file {file_path} is not inside the workspace {ws}")
        typer.echo("❌ The file is not inside the workspace")
        raise typer.Exit(1)
    return ws, rel_to_ws

def _get_crate_info(file_path: Path) -> tuple[str, Path]:
    """Return crate name and crate root for a file, or exit if not found."""
    crate_name, crate_root = find_containing_crate(file_path)
    print(f"==> Crate name: {crate_name}, crate root: {crate_root}")
    if not crate_name or not crate_root:
        print(f"==> ERROR: Could not determine crate for the file {file_path}")
        typer.echo("❌ Could not determine crate for the file")
        raise typer.Exit(1)
    return crate_name, crate_root

def _find_integration_test_cmd(
    file_path: Path, parts: tuple, crate_root: Path, pkg_flag: str
) -> str:
    idx = parts.index('tests')
    print(f"==> 'tests' found at index {idx} in path parts")
    target_module = parts[idx + 1] if len(parts) > idx + 1 else None
    print(f"==> Target module: {target_module}")
    test_binary = None
    crate_tests_dir = crate_root / 'tests'
    print(f"==> Crate tests dir: {crate_tests_dir}")
    scan_dir = file_path.parent
    print(f"==> Initial scan_dir: {scan_dir}")
    if target_module:
        while True:
            print(f"==> Scanning directory: {scan_dir}")
            for rs in scan_dir.glob('*.rs'):
                print(f"==> Checking file: {rs}")
                content = rs.read_text(encoding='utf-8')
                if re.search(rf"mod\s+{target_module}\s*;", content):
                    print(f"==> Found mod declaration for {target_module} in {rs}")
                    test_binary = rs.stem
                    break
            if test_binary or scan_dir.resolve() == crate_tests_dir.resolve():
                print(f"==> Breaking scan loop: test_binary={test_binary}, scan_dir={scan_dir}")
                break
            scan_dir = scan_dir.parent
    if not test_binary:
        mod_name = file_path.stem
        missing_mod = f"mod {mod_name};"
        
        # Find the exact break point in the chain
        if target_module:
            # Should have found mod declaration for target_module in parent of target_module directory
            break_point = file_path.parent.parent  # Go up one more level to where mod declaration should be
            expected_in = f"mod {target_module};"
        else:
            # File is directly in tests/, should have mod declaration for the file itself
            break_point = crate_tests_dir
            expected_in = missing_mod
        
        # Look for .rs files in the break point directory
        rs_files = list(break_point.glob('*.rs'))
        
        msg = f"The test file {file_path} is unreachable by mod declaration.\n"
        msg += f"Missing '{expected_in}' in {break_point}/"
        
        if rs_files:
            if len(rs_files) == 1:
                msg += f"{rs_files[0].name}"
            else:
                rs_names = [f.name for f in rs_files]
                msg += f"[{', '.join(rs_names)}]"
        else:
            msg += "*.rs (no .rs files found)"
        
        print(f"==> ERROR: {msg}")
        typer.echo(f"❌ {msg}")
        raise typer.Exit(1)
    cmd = f"cargo test {pkg_flag} --test {test_binary}"
    print(f"==> Test command for integration test: {cmd}")
    return cmd

def _find_unit_test_cmd(file_path: Path, crate_root: Path, pkg_flag: str) -> str:
    rel_crate = file_path.resolve().relative_to(crate_root)
    print(f"==> File relative to crate root: {rel_crate}")
    parts2 = [p for p in rel_crate.with_suffix('').parts if p not in ('src', 'mod')]
    print(f"==> Module path parts: {parts2}")
    module_path = '::'.join(parts2)
    print(f"==> Module path: {module_path}")
    cmd = f"cargo test {pkg_flag} {module_path}" if module_path else f"cargo test {pkg_flag}"
    print(f"==> Test command for unit test/example: {cmd}")
    return cmd

@app.command()
def craft_test(file_path: Path):
    """
    Craft a `cargo test -p <package> --test <testfile>` command to run tests in the specified Rust source file.
    It scans the entire `tests/` directory for `mod <module>;` declarations.
    """
    print(f"==> craft_test called with file_path: {file_path}")
    ws, rel_to_ws = _get_workspace_and_relative_path(file_path)
    crate_name, crate_root = _get_crate_info(file_path)
    pkg_flag = f"-p {crate_name}"
    parts = rel_to_ws.with_suffix('').parts
    print(f"==> Path parts: {parts}")
    if 'tests' in parts:
        cmd = _find_integration_test_cmd(file_path, parts, crate_root, pkg_flag)
    else:
        cmd = _find_unit_test_cmd(file_path, crate_root, pkg_flag)
    typer.echo(f"🔧 Test command: {cmd}")

if __name__ == "__main__":
    app()
