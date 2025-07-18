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
        # First check if there's a mod.rs in the same directory that should declare this file
        mod_rs_path = file_path.parent / "mod.rs"
        found_in_mod_rs = False
        
        if mod_rs_path.exists():
            print(f"==> Checking mod.rs in same directory: {mod_rs_path}")
            content = mod_rs_path.read_text(encoding='utf-8')
            file_stem = file_path.stem
            if re.search(rf"mod\s+{file_stem}\s*;", content):
                print(f"==> Found mod declaration for {file_stem} in {mod_rs_path}")
                found_in_mod_rs = True
                # Get the parent directory name as the test binary
                test_binary = file_path.parent.name
                print(f"==> Test binary from parent dir: {test_binary}")
            else:
                print(f"==> mod.rs exists but does not contain 'mod {file_stem};'")
                # mod.rs exists but doesn't declare this file - this is an error
                # Don't continue scanning, show error immediately
                pass
        
        # If mod.rs exists but doesn't declare the file, show error
        if mod_rs_path.exists() and not found_in_mod_rs:
            test_binary = None  # Force error
            print(f"==> Forcing error: mod.rs exists but missing 'mod {file_stem};'")
            print(f"==> DEBUG: found_in_mod_rs={found_in_mod_rs}, will set test_binary=None")
        # If no mod.rs, continue with original scanning logic
        elif not mod_rs_path.exists():
            print(f"==> No mod.rs found, continuing scan")
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
    print(f"==> Final test_binary value: {test_binary}")
    if not test_binary:
        mod_name = file_path.stem
        
        # Build a detailed chain analysis
        msg_parts = []
        msg_parts.append(f"🎯 Test file: {file_path}")
        msg_parts.append(f"📁 Parent directory: {file_path.parent}")
        
        # Check for mod.rs in parent directory
        mod_rs_path = file_path.parent / "mod.rs"
        if mod_rs_path.exists():
            msg_parts.append(f"✅ Found mod.rs: {mod_rs_path}")
            content = mod_rs_path.read_text(encoding='utf-8')
            file_stem = file_path.stem
            
            # Check if this specific file is declared
            pattern = rf"mod\s+{file_stem}\s*;"
            if re.search(pattern, content):
                msg_parts.append(f"✅ Found declaration: 'mod {file_stem};' in {mod_rs_path.name}")
            else:
                msg_parts.append(f"❌ MISSING: 'mod {file_stem};' in {mod_rs_path.name}")
                msg_parts.append(f"   Expected declaration: mod {file_stem};")
                msg_parts.append("")
                msg_parts.append("🔍 Current mod.rs content:")
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'mod' in line and not line.strip().startswith('//'):
                        msg_parts.append(f"   {i:3}: {line}")
        else:
            msg_parts.append(f"❌ No mod.rs found in: {file_path.parent}")
            
            # Check parent directories for mod declarations
            current_dir = file_path.parent
            while current_dir != crate_tests_dir and current_dir != current_dir.parent:
                parent = current_dir.parent
                mod_rs_in_parent = parent / "mod.rs"
                
                if mod_rs_in_parent.exists():
                    msg_parts.append(f"\n📁 Checking parent: {parent}")
                    content = mod_rs_in_parent.read_text(encoding='utf-8')
                    dir_name = current_dir.name
                    
                    if re.search(rf"mod\s+{dir_name}\s*;", content):
                        msg_parts.append(f"✅ Found: mod {dir_name}; in {mod_rs_in_parent}")
                    else:
                        msg_parts.append(f"❌ MISSING: mod {dir_name}; in {mod_rs_in_parent}")
                        break
                else:
                    msg_parts.append(f"❌ No mod.rs in parent: {parent}")
                    
                current_dir = parent
        
        # Show the complete mod chain that should exist
        msg_parts.append("\n🔄 Expected mod chain:")
        rel_path = file_path.relative_to(crate_tests_dir)
        parts = list(rel_path.with_suffix('').parts)
        
        if len(parts) == 1:
            # Direct file in tests/
            expected_line = f"mod {parts[0]};"
            msg_parts.append(f"   {crate_tests_dir}/mod.rs should contain: {expected_line}")
        else:
            # Nested structure
            current_path = crate_tests_dir
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # Last part is the file itself
                    expected_line = f"mod {part};"
                    msg_parts.append(f"   {current_path}/mod.rs should contain: {expected_line}")
                else:
                    # Intermediate directory
                    expected_line = f"mod {part};"
                    msg_parts.append(f"   {current_path}/mod.rs should contain: {expected_line}")
                    current_path = current_path / part
        
        # List all .rs files in relevant directories for context
        msg_parts.append(f"\n📋 Context:")
        msg_parts.append(f"Crate tests directory: {crate_tests_dir}")
        
        # List files in the parent directory
        parent_files = list(file_path.parent.glob('*.rs'))
        if parent_files:
            msg_parts.append(f"Files in {file_path.parent}:")
            for f in sorted(parent_files):
                marker = "👉 " if f == file_path else "   "
                msg_parts.append(f"{marker}{f.name}")
        
        # List files in crate tests directory
        if crate_tests_dir != file_path.parent:
            tests_files = list(crate_tests_dir.glob('*.rs'))
            if tests_files:
                msg_parts.append(f"Files in {crate_tests_dir}:")
                for f in sorted(tests_files):
                    msg_parts.append(f"   {f.name}")
        
        msg = "\n".join(msg_parts)
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
