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
    
    # Get the relative path from tests directory
    rel_path_parts = parts[idx + 1:]  # Everything after 'tests'
    print(f"==> Relative path parts: {rel_path_parts}")
    
    crate_tests_dir = crate_root / 'tests'
    print(f"==> Crate tests dir: {crate_tests_dir}")
    
    if not rel_path_parts:
        # File is directly in tests/, use filename as binary
        test_binary = file_path.stem
        test_file = crate_tests_dir / f"{test_binary}.rs"
        if test_file.exists():
            return f"cargo test {pkg_flag} --test {test_binary}"
        else:
            raise RuntimeError(f"{file_path} is not reachable.\nNo test binary found")
    
    # Get the target module (e.g., 'parquet')
    target_module = rel_path_parts[0]
    print(f"==> Target module: {target_module}")
    
    # Look for test binary files in the tests directory
    test_binaries = [f.stem for f in crate_tests_dir.glob('*.rs')]
    print(f"==> Available test binaries: {test_binaries}")
    
# Check complete mod chain from test binary down to the final file
    crate_tests_dir = crate_root / 'tests'
    
    # Build the complete path from tests directory
    current_path = crate_tests_dir
    path_parts = rel_path_parts
    
    if not path_parts:
        # File is directly in tests/
        test_binary = file_path.stem
        test_file = crate_tests_dir / f"{test_binary}.rs"
        if test_file.exists():
            return f"cargo test {pkg_flag} --test {test_binary}"
        else:
            raise RuntimeError(f"{file_path} is not reachable.\nNo test binary found")
    
    # Step 1: Find test binary that contains the first module
    first_module = path_parts[0]
    test_binaries = [f.stem for f in crate_tests_dir.glob('*.rs')]
    test_binary = None
    
    for test_file_stem in test_binaries:
        test_file_path = crate_tests_dir / f"{test_file_stem}.rs"
        if test_file_path.exists():
            content = test_file_path.read_text(encoding='utf-8')
            if re.search(rf"mod\s+{first_module}\s*;", content):
                test_binary = test_file_stem
                break
    
    if not test_binary:
        msg = f"{file_path} is not reachable.\nNo test binary contains 'mod {first_module}'.\nTest binaries scanned: {', '.join(sorted(test_binaries))}"
        raise RuntimeError(msg)
    
    # Step 2: Check the complete chain
    current_path = crate_tests_dir
    print(f"==> DEBUG: Checking chain for path_parts: {path_parts}")
    
    for i, part in enumerate(path_parts):
        print(f"==> DEBUG: Checking part {i}: '{part}'")
        if i == 0:
            # First level handled by test binary
            current_path = current_path / part
            print(f"==> DEBUG: First level, moving to: {current_path}")
            continue
            
        # Check mod.rs in parent directory for this part
        parent_mod_rs = current_path.parent / "mod.rs"
        print(f"==> DEBUG: Checking {parent_mod_rs} for 'mod {part}'")
        
        if parent_mod_rs.exists():
            content = parent_mod_rs.read_text(encoding='utf-8')
            if re.search(rf"mod\s+{part}\s*;", content):
                print(f"==> DEBUG: Found 'mod {part}' in {parent_mod_rs}")
            else:
                print(f"==> DEBUG: Missing 'mod {part}' in {parent_mod_rs}")
                msg = f"{file_path} is not reachable.\n{parent_mod_rs} does not contain 'mod {part}'"
                raise RuntimeError(msg)
        else:
            print(f"==> DEBUG: {parent_mod_rs} does not exist")
        
        # Move to next level
        current_path = current_path / part
        print(f"==> DEBUG: Moving to next level: {current_path}")
    
    # Step 3: Check final file declaration
    parent_dir = current_path.parent
    final_mod_rs = parent_dir / "mod.rs"
    
    if final_mod_rs.exists():
        content = final_mod_rs.read_text(encoding='utf-8')
        if not re.search(rf"mod\s+{file_path.stem}\s*;", content):
            msg = f"{file_path} is not reachable.\n{final_mod_rs} does not contain 'mod {file_path.stem}'"
            raise RuntimeError(msg)
    
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
    try:
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
    except ValueError as e:
        if "not in the subpath" in str(e):
            abs_file = file_path.resolve()
            abs_crate = Path.cwd().resolve()
            crate_rel = abs_file.relative_to(abs_crate) if abs_crate in abs_file.parents else None
            
            msg_parts = [
                f"🎯 File: {file_path}",
                f"📁 Absolute path: {abs_file}",
                f"🏠 Current directory: {abs_crate}",
            ]
            
            if crate_rel:
                msg_parts.extend([
                    f"📊 Relative to crate: {crate_rel}",
                    "",
                    "💡 To fix this, run the command from:",
                    f"   cd {abs_crate}",
                    f"   python rust_tools.py craft-test {crate_rel}"
                ])
            else:
                msg_parts.extend([
                    "",
                    "❌ This file is outside the current workspace",
                    "💡 Ensure you're in the correct directory or use absolute path"
                ])
            
            typer.echo(f"❌ Path Error: {' '.join(msg_parts)}")
            raise typer.Exit(1)
        else:
            typer.echo(f"❌ Error: {e}")
            raise typer.Exit(1)
    except RuntimeError as e:
        # This catches the detailed mod chain errors from _find_integration_test_cmd
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
