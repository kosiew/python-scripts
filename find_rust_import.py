import os
import re
import sys
from pathlib import Path

def find_workspace_root(start_dir):
    current = Path(start_dir).resolve()
    while current != current.parent:
        cargo_toml = current / "Cargo.toml"
        if cargo_toml.exists():
            with open(cargo_toml, "r", encoding="utf-8") as f:
                if "[workspace]" in f.read():
                    return current
        current = current.parent
    return None

def find_crate_name(directory):
    """Extract the crate name from Cargo.toml in the specified directory"""
    cargo_path = os.path.join(directory, "Cargo.toml")
    if not os.path.exists(cargo_path):
        return None
        
    try:
        with open(cargo_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'\[package\][^\[]*name\s*=\\s*"([^"]+)"', content, re.DOTALL)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"⚠️ Error reading Cargo.toml: {e}")
    
    return None

def find_containing_crate(directory):
    """
    Find the crate that contains the specified directory.
    Returns a tuple (crate_name, crate_root_dir)
    """
    current = Path(directory).resolve()
    
    # Look upward until we find a Cargo.toml
    while current != current.parent:
        cargo_toml = current / "Cargo.toml"
        if cargo_toml.exists():
            try:
                with open(cargo_toml, "r", encoding="utf-8") as f:
                    content = f.read()
                    match = re.search(r'\[package\][^\[]*name\s*=\s*"([^"]+)"', content, re.DOTALL)
                    if match:
                        return (match.group(1), current)
            except Exception as e:
                print(f"⚠️ Error reading {cargo_toml}: {e}")
                
        # Special case: if we find src/lib.rs or src/main.rs, this is likely a crate root
        src_dir = current / "src"
        if src_dir.exists() and (src_dir / "lib.rs").exists():
            # Still need to get the name from Cargo.toml
            if cargo_toml.exists():
                try:
                    with open(cargo_toml, "r", encoding="utf-8") as f:
                        content = f.read()
                        match = re.search(r'\[package\][^\[]*name\s*=\s*"([^"]+)"', content, re.DOTALL)
                        if match:
                            return (match.group(1), current)
                except Exception:
                    pass
        
        current = current.parent
    
    return (None, None)

def find_rust_struct(root_dir, struct_name):
    matches = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".rs"):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        match = re.search(rf"pub\s+struct\s+{struct_name}\b", content)
                        if match:
                            matches.append(filepath)
                except Exception as e:
                    print(f"⚠️ Skipping {filepath}: {e}")
    return matches

def find_re_exports(root_dir, struct_name):
    exports = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".rs"):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Match pub use ...::StructName;
                        for match in re.finditer(rf"pub\s+use\s+(.+?)::({struct_name})\s*;", content):
                            full_path = match.group(1) + "::" + match.group(2)
                            relative_path = os.path.relpath(filepath, root_dir)
                            exports.append((relative_path, full_path))
                except Exception as e:
                    continue
    return exports

def get_module_path(filepath, root_dir):
    relative_path = os.path.relpath(filepath, root_dir)
    parts = relative_path.replace(".rs", "").split(os.sep)

    if parts[-1] == "mod":
        parts = parts[:-1]
    if "src" in parts:
        parts.remove("src")

    return "::".join(parts)

def find_correct_import(root_dir, struct_name, workspace_root=None):
    struct_files = find_rust_struct(root_dir, struct_name)
    re_exports = find_re_exports(root_dir, struct_name)

    if not struct_files:
        print(f"❌ Struct `{struct_name}` not found in {root_dir}")
        return None

    print(f"✅ Found `{struct_name}` defined in:")
    for file in struct_files:
        # Convert to relative path if workspace_root is provided
        display_path = os.path.relpath(file, workspace_root) if workspace_root else file
        print(f"   - {display_path}")

    use_statements = []

    # Direct paths
    for file in struct_files:
        module_path = get_module_path(file, root_dir)
        use_statements.append((f"use {module_path}::{struct_name};", "direct"))

    # Re-exports
    for rel_path, reexport in re_exports:
        # Normalize re-exported use
        if reexport.startswith("crate::"):
            short_path = f"use crate::{struct_name};"
            use_statements.append((short_path, f"re-exported via {rel_path}"))
        else:
            use_statements.append((f"use {reexport};", f"re-exported via {rel_path}"))

    return use_statements

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python find_rust_import.py <StructName>")
        sys.exit(1)

    struct_name = sys.argv[1]
    current_dir = os.getcwd()
    workspace_root = find_workspace_root(current_dir)
    current_dir_relative = os.path.relpath(current_dir, workspace_root) if workspace_root else current_dir
    print(f"📂 Current directory: {current_dir_relative}")
    if not workspace_root:
        print("❌ Could not find the workspace root (Cargo.toml with [workspace])")
        sys.exit(1)

    # Find the containing crate for the current directory
    crate_name, crate_root = find_containing_crate(current_dir)
    if crate_name:
        crate_rel_path = os.path.relpath(crate_root, workspace_root) if workspace_root else str(crate_root)
        print(f"🦀 Current crate: {crate_name} ({crate_rel_path})")
    else:
        print("❌ Could not find the containing crate for the current directory")

    print(f"📦 Workspace root: {workspace_root}")
    print(f"🔍 Searching for `{struct_name}`...\n")

    use_statements = find_correct_import(str(workspace_root), struct_name, workspace_root)

    if use_statements:
        print("\n🎯 Suggested `use` statements:")
        for stmt, note in use_statements:
            print(f"   {stmt}   // {note}")
