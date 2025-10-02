import os
import re
import subprocess
import shutil
import sys
from pathlib import Path
import typer

app = typer.Typer(help="CLI tool to find Rust imports and generate test commands for a given struct or file")


DEBUG = False

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)



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
        if not crate or not crate_root:
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
    if crate and crate_root:
        try:
            rel_crate_root = crate_root.relative_to(ws)
        except Exception:
            rel_crate_root = crate_root
        typer.echo(f"🦀 Current crate: {crate} ({rel_crate_root})")
    else:
        typer.echo("❌ Could not determine current crate")
    typer.echo(f"🔍 Searching for `{struct_name}`...\n")
    use_statements = find_correct_import(ws, struct_name, ws, crate)
    if use_statements:
        typer.echo("🎯 Suggested `use` statements:")
        for stmt, note in use_statements:
            typer.echo(f"  {stmt}  // {note}")

def _get_workspace_and_relative_path(file_path: Path) -> tuple[Path, Path]:
    """Return workspace root and file path relative to workspace, or exit if not inside workspace."""
    cwd = Path(os.getcwd())
    debug_print(f"==> Current working directory: {cwd}")
    ws = find_workspace_root(cwd) or cwd
    debug_print(f"==> Workspace root: {ws}")
    try:
        rel_to_ws = file_path.resolve().relative_to(ws)
        debug_print(f"==> File relative to workspace: {rel_to_ws}")
    except ValueError:
        debug_print(f"==> ERROR: The file {file_path} is not inside the workspace {ws}")
        typer.echo("❌ The file is not inside the workspace")
        raise typer.Exit(1)
    return ws, rel_to_ws

def _get_crate_info(file_path: Path) -> tuple[str, Path]:
    """Return crate name and crate root for a file, or exit if not found."""
    crate_name, crate_root = find_containing_crate(file_path)
    debug_print(f"==> Crate name: {crate_name}, crate root: {crate_root}")
    if not crate_name or not crate_root:
        debug_print(f"==> ERROR: Could not determine crate for the file {file_path}")
        typer.echo("❌ Could not determine crate for the file")
        raise typer.Exit(1)
    return crate_name, crate_root

def _find_integration_test_cmd(
    file_path: Path, parts: tuple, crate_root: Path, pkg_flag: str
) -> str:
    idx = parts.index('tests')
    debug_print(f"==> 'tests' found at index {idx} in path parts")
    
    # Get the relative path from tests directory
    rel_path_parts = parts[idx + 1:]  # Everything after 'tests'
    debug_print(f"==> Relative path parts: {rel_path_parts}")
    crate_tests_dir = crate_root / 'tests'
    debug_print(f"==> Crate tests dir: {crate_tests_dir}")

    if not rel_path_parts:
        return _find_test_binary_for_file_in_tests(file_path, crate_tests_dir, pkg_flag)

    # Handle direct test files in tests directory
    if len(rel_path_parts) == 1:
        # This is a test file directly in tests directory
        test_binary = rel_path_parts[0]
        test_file = crate_tests_dir / f"{test_binary}.rs"
        if test_file.exists():
            return f"cargo test {pkg_flag} --test {test_binary}"
        else:
            # Try to find it as a module within another test binary
            test_binary = _find_test_binary_for_module(crate_tests_dir, rel_path_parts[0], file_path)
            return f"cargo test {pkg_flag} --test {test_binary}"
    
    # Handle integration test structure with subdirectories
    if len(rel_path_parts) >= 2:
        # Case: schema_adapter/schema_adapter_integration_tests
        # We need to find which test binary contains this module
        
        # First, check if the last part is a test file in a subdirectory
        test_name = rel_path_parts[-1]
        directory_name = rel_path_parts[-2]
        
        # Get all available test binaries (.rs files in tests directory)
        available_test_binaries = [f.stem for f in crate_tests_dir.glob('*.rs')]
        
        if available_test_binaries:
            # Look for test binaries that contain the directory as a module
            for test_binary in available_test_binaries:
                test_file = crate_tests_dir / f"{test_binary}.rs"
                if test_file.exists():
                    content = test_file.read_text(encoding='utf-8')
                    # Check if this test binary has a mod declaration for the directory
                    mod_pattern = rf"^\s*(pub(\s*\([^)]*\))?\s+)?mod\s+{directory_name}\b"
                    if re.search(mod_pattern, content, re.MULTILINE):
                        return f"cargo test {pkg_flag} --test {test_binary} -- {directory_name}"
        
        # If no specific test binary found with the module, use directory name
        test_binary = directory_name
        test_file = crate_tests_dir / f"{test_binary}.rs"
        if test_file.exists():
            return f"cargo test {pkg_flag} --test {test_binary}"
    
    # Check for direct test files
    if len(rel_path_parts) >= 1 and rel_path_parts[-1].endswith('.rs'):
        test_binary = rel_path_parts[-1][:-3]  # Remove .rs extension
        test_file = crate_tests_dir / f"{test_binary}.rs"
        if test_file.exists():
            return f"cargo test {pkg_flag} --test {test_binary}"
    
    # Use the original logic to find the test binary
    test_binary = _find_test_binary_for_module(crate_tests_dir, rel_path_parts[0], file_path)
    
    # For nested structures, add the remaining parts as module path
    if len(rel_path_parts) > 1:
        # Find the module path from the remaining parts
        remaining_parts = list(rel_path_parts[1:])

        # If the last part is a `mod` (from mod.rs), drop it so we don't append '::mod'
        if remaining_parts and remaining_parts[-1] == 'mod':
            remaining_parts = remaining_parts[:-1]

        # If the last part is a .rs file, use its directory as module path
        if remaining_parts and remaining_parts[-1].endswith('.rs'):
            module_path = "::".join(remaining_parts[:-1])  # Just the directory path
            if module_path:
                cmd = f"cargo test {pkg_flag} --test {test_binary} -- {module_path}"
            else:
                cmd = f"cargo test {pkg_flag} --test {test_binary}"
        elif remaining_parts:
            module_path = "::".join(remaining_parts)
            cmd = f"cargo test {pkg_flag} --test {test_binary} -- {module_path}"
        else:
            # No remaining parts after stripping 'mod' -> run whole test binary
            cmd = f"cargo test {pkg_flag} --test {test_binary}"
    else:
        cmd = f"cargo test {pkg_flag} --test {test_binary}"
    
    debug_print(f"==> Test command for integration test: {cmd}")
    return cmd


def _find_test_binary_for_file_in_tests(file_path: Path, crate_tests_dir: Path, pkg_flag: str) -> str:
    """
    If the file is directly in tests/, use filename as binary.
    """
    test_binary = file_path.stem
    test_file = crate_tests_dir / f"{test_binary}.rs"
    if test_file.exists():
        return f"cargo test -p {pkg_flag} --test {test_binary}" if pkg_flag else f"cargo test --test {test_binary}"
    else:
        raise RuntimeError(f"{file_path} is not reachable.\nNo test binary found")


def _find_test_binary_for_module(crate_tests_dir: Path, first_module: str, file_path: Path) -> str:
    """
    Find the test binary that contains the first module declaration.
    """
    test_binaries = [f.stem for f in crate_tests_dir.glob('*.rs')]
    debug_print(f"==> Available test binaries: {test_binaries}")
    mod_pattern = rf"^\s*(pub(\s*\([^)]*\))?\s+)?mod\s+{first_module}\b"
    for test_file_stem in test_binaries:
        test_file_path = crate_tests_dir / f"{test_file_stem}.rs"
        if test_file_path.exists():
            content = test_file_path.read_text(encoding='utf-8')
            for line in content.splitlines():
                if re.match(mod_pattern, line):
                    debug_print(f"==> Found 'mod {first_module}' in {test_file_path}")
                    return test_file_stem
    msg = f"{file_path} is not reachable.\nNo test binaries contain 'mod {first_module}'.\nFiles scanned: {', '.join(sorted(test_binaries))}"
    raise RuntimeError(msg)


def _check_mod_chain(crate_tests_dir: Path, path_parts: tuple, file_path: Path) -> None:
    """
    Check the complete mod chain from the test binary down to the final file.
    """
    check_path = crate_tests_dir
    for i, part in enumerate(path_parts):
        if i == 0:
            check_path = check_path / part
            continue
        mod_rs_path = check_path / "mod.rs"
        debug_print(f"==> DEBUG: Checking {mod_rs_path} for 'mod {part}'")
        if mod_rs_path.exists():
            content = mod_rs_path.read_text(encoding='utf-8')
            mod_pattern = rf"^\s*(pub(\s*\([^)]*\))?\s+)?mod\s+{part}\b"
            found_mod = False
            for line in content.splitlines():
                if re.match(mod_pattern, line):
                    found_mod = True
                    break
            if found_mod:
                debug_print(f"==> DEBUG: Found 'mod {part}' in {mod_rs_path}")
            else:
                debug_print(f"==> DEBUG: Missing 'mod {part}' in {mod_rs_path}")
                msg = f"{file_path} is not reachable.\n{mod_rs_path} does not contain 'mod {part}'"
                raise RuntimeError(msg)
        else:
            debug_print(f"==> DEBUG: {mod_rs_path} does not exist")
        check_path = check_path / part
    # Final check - the actual file
    final_mod_rs = check_path.parent / "mod.rs"
    debug_print(f"==> DEBUG: Checking final file: {final_mod_rs}")
    if final_mod_rs.exists():
        content = final_mod_rs.read_text(encoding='utf-8')
        mod_pattern = rf"^\s*(pub(\s*\([^)]*\))?\s+)?mod\s+{file_path.stem}\b"
        found_mod = False
        for line in content.splitlines():
            if re.match(mod_pattern, line):
                found_mod = True
                break
        if found_mod:
            debug_print(f"==> DEBUG: Found 'mod {file_path.stem}' in {final_mod_rs}")
        else:
            debug_print(f"==> DEBUG: Missing 'mod {file_path.stem}' in {final_mod_rs}")
            msg = f"{file_path} is not reachable.\n{final_mod_rs} does not contain 'mod {file_path.stem}'"
            raise RuntimeError(msg)
    else:
        debug_print(f"==> DEBUG: Final mod.rs {final_mod_rs} does not exist")

def _find_unit_test_cmd(file_path: Path, crate_root: Path, pkg_flag: str) -> str:
    rel_crate = file_path.resolve().relative_to(crate_root)
    debug_print(f"==> File relative to crate root: {rel_crate}")
    parts2 = [p for p in rel_crate.with_suffix('').parts if p not in ('src', 'mod')]
    debug_print(f"==> Module path parts: {parts2}")
    module_path = '::'.join(parts2)
    debug_print(f"==> Module path: {module_path}")
    cmd = f"cargo test {pkg_flag} {module_path}" if module_path else f"cargo test {pkg_flag}"
    debug_print(f"==> Test command for unit test/example: {cmd}")
    return cmd


def _copy_ctest_variant_to_clipboard(cmd: str) -> None:
    """
    Create a `ctest`-prefixed variant of `cmd` and attempt to copy it to the macOS clipboard.
    On non-mac platforms print the ctest variant instead.
    """
    try:
        ctest_cmd = re.sub(r'^\s*cargo\s+test', 'ctest', cmd, count=1)
        # Prefer pbcopy on macOS
        if sys.platform == 'darwin' and shutil.which('pbcopy'):
            subprocess.run(['pbcopy'], input=ctest_cmd.encode('utf-8'), check=False)
            typer.echo(f"📋 Copied to clipboard: {ctest_cmd}")
        elif sys.platform == 'darwin':
            # Fallback to osascript if pbcopy missing
            safe = ctest_cmd.replace('"', '\\"')
            subprocess.run(['osascript', '-e', f'set the clipboard to "{safe}"'], check=False)
            typer.echo(f"📋 Copied to clipboard via osascript: {ctest_cmd}")
        else:
            typer.echo("⚠️ Clipboard copy not supported on this platform; here is the ctest variant:")
            typer.echo(ctest_cmd)
    except Exception as e:
        typer.echo(f"⚠️ Could not copy to clipboard: {e}")

@app.command()
def craft_test(file_path: Path):
    """
    Craft a `cargo test -p <package> --test <testfile>` command to run tests in the specified Rust source file.
    It scans the entire `tests/` directory for `mod <module>;` declarations.
    """
    debug_print(f"==> craft_test called with file_path: {file_path}")
    try:
        # Support multiple paths: either a file containing multiple lines or a single Path
        cmds: list[str] = []

        # If file_path refers to a file named '-' treat it as clipboard/multi-line input from stdin
        raw_input = None
        if str(file_path) == "-":
            # Read from stdin for pasted multi-line paths
            raw_input = sys.stdin.read()
            debug_print("==> Read multi-path input from stdin")
            paths = [line.strip() for line in raw_input.splitlines() if line.strip()]
        else:
            # Single path provided; but allow the path to point to a file containing multiple lines
            # e.g., a temp file with multiple paths
            p = Path(file_path)
            if p.exists() and p.is_file():
                # Try to detect if file contains multiple lines that look like paths
                content = p.read_text(encoding='utf-8')
                if "\n" in content:
                    paths = [line.strip() for line in content.splitlines() if line.strip()]
                else:
                    paths = [str(p)]
            else:
                # Path may be relative/doesn't exist as file but is intended as source path
                paths = [str(file_path)]

        for p in paths:
            fp = Path(p)
            # Normalize relative paths against cwd
            if not fp.is_absolute():
                fp = Path(os.getcwd()) / fp

            ws, rel_to_ws = _get_workspace_and_relative_path(fp)
            crate_name, crate_root = _get_crate_info(fp)
            pkg_flag = f"-p {crate_name}"
            parts = rel_to_ws.with_suffix('').parts
            debug_print(f"==> Path parts: {parts}")
            if 'tests' in parts:
                cmd = _find_integration_test_cmd(fp, parts, crate_root, pkg_flag)
            else:
                cmd = _find_unit_test_cmd(fp, crate_root, pkg_flag)
            cmds.append(cmd)

        # If multiple commands, produce a ctest variant joined by && and copy to clipboard
        if len(cmds) == 1:
            final_cmd = cmds[0]
            _copy_ctest_variant_to_clipboard(final_cmd)
            typer.echo(final_cmd)
        else:
            joined = ' && '.join(re.sub(r'^\s*cargo\s+test', 'ctest', c, count=1) for c in cmds)
            # Copy the combined ctest chain to clipboard (or print fallback)
            _copy_ctest_variant_to_clipboard(joined)
            typer.echo(joined)
        typer.echo(f"🔧 Test command:\n{cmd}")
        # Copy `ctest` variant to clipboard (extracted helper)
        _copy_ctest_variant_to_clipboard(cmd)
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
