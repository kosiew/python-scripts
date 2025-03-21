import os
import re
import sys
import json
import subprocess
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

def normalize_crate_name(name):
    """Convert crate name to the format used in imports (replacing hyphens with underscores)"""
    return name.replace("-", "_")

def get_crate_dependencies(directory):
    """Extract dependencies from Cargo.toml"""
    cargo_path = os.path.join(directory, "Cargo.toml")
    if not os.path.exists(cargo_path):
        return []
        
    dependencies = []
    try:
        with open(cargo_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Extract dependencies section
            dep_section = re.search(r'\[dependencies\](.*?)(\[|\Z)', content, re.DOTALL)
            if dep_section:
                deps_text = dep_section.group(1)
                # Extract dependency names
                for line in deps_text.split('\n'):
                    # Simple case: dependency = "version"
                    simple_match = re.match(r'^\s*([a-zA-Z0-9_-]+)\s*=', line)
                    if simple_match:
                        dependencies.append(simple_match.group(1))
                    # Table format: [dependencies.name]
                    table_match = re.match(r'^\s*\[dependencies\.([a-zA-Z0-9_-]+)\]', line)
                    if table_match:
                        dependencies.append(table_match.group(1))
    except Exception as e:
        print(f"⚠️ Error reading dependencies from Cargo.toml: {e}")
    
    return dependencies

def find_correct_import(root_dir, struct_name, workspace_root=None, current_crate=None):
    struct_files = find_rust_struct(root_dir, struct_name)
    re_exports = find_re_exports(root_dir, struct_name)

    # If the struct isn't found in the workspace, check if it might be from an external dependency
    if not struct_files:
        # Get dependencies from the current Cargo.toml
        if current_crate:
            external_deps = get_crate_dependencies(os.path.dirname(current_dir))
            
            print(f"❌ Struct `{struct_name}` not found in {root_dir}")
            # Suggest common imports that might match
            suggestions = []
            for dep in external_deps:
                normalized_dep = normalize_crate_name(dep)
                suggestions.append(f"use {normalized_dep}::{struct_name};")
            
            if suggestions:
                print("\nPossible imports to try:")
                for suggestion in suggestions[:3]:  # Limit to 3 suggestions
                    print(f"  {suggestion}")
                    
            return None
        else:
            print(f"❌ Struct `{struct_name}` not found in {root_dir}")
            return None

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
        file_crate, file_crate_root = find_containing_crate(file)
        if not file_crate:
            continue
            
        # Get the relative path within the crate
        crate_relative_path = os.path.relpath(file, file_crate_root)
        parts = crate_relative_path.replace(".rs", "").split(os.sep)
        
        # Remove common parts like "src"
        if "src" in parts:
            parts.remove("src")
        if parts[-1] == "mod":
            parts = parts[:-1]
            
        module_path = "::".join(parts) if parts else ""
        
        # Generate import based on crate relationship
        if current_crate and current_crate != file_crate:
            # Importing from another crate in the workspace - use the direct crate name
            # Convert hyphenated crate names to underscores as Rust does
            normalized_crate = normalize_crate_name(file_crate)
            
            # Do NOT use the workspace name (e.g., datafusion) in the import
            if module_path:
                import_path = f"use {normalized_crate}::{module_path}::{struct_name};"
            else:
                import_path = f"use {normalized_crate}::{struct_name};"
            use_statements.append((import_path, "direct (from another crate)"))
        else:
            # Same crate
            if module_path:
                import_path = f"use crate::{module_path}::{struct_name};"
            else:
                import_path = f"use crate::{struct_name};"
            use_statements.append((import_path, "direct (same crate)"))

    # Re-exports 
    # (update this section as well to avoid circular dependencies)
    for rel_path, reexport in re_exports:
        # Avoid any re-exports that would cause circular dependencies
        if current_crate and (reexport.startswith("datafusion::") or "::datafusion::" in reexport):
            continue
        
        # Only include re-exports that could be useful
        if reexport.startswith("crate::"):
            short_path = f"use crate::{struct_name};"
            use_statements.append((short_path, f"re-exported via {rel_path}"))
        else:
            use_statements.append((f"use {reexport};", f"re-exported via {rel_path}"))

    return use_statements

def check_rust_analyzer_installed():
    """Check if rust-analyzer is installed and available"""
    try:
        subprocess.run(["rust-analyzer", "--version"], capture_output=True, check=False)
        return True
    except FileNotFoundError:
        return False

def query_rust_analyzer(workspace_root, struct_name):
    """
    Use rust-analyzer to find the definition of a struct
    Returns a tuple (source_file, crate_name, module_path)
    """
    try:
        # Create a temporary Rust file with the struct name
        temp_dir = os.path.join(workspace_root, "target", "temp_ra")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, "temp.rs")
        
        # Write a sample usage of the struct to the temp file
        with open(temp_file, "w") as f:
            f.write(f"fn main() {{ let _x: {struct_name}; }}")
        
        # Run rust-analyzer to find the definition
        cmd = [
            "rust-analyzer", "analysis-stats", 
            "--wait-for-input", "--json",
            f"--goto-def={temp_file}:1:21"
        ]
        
        result = subprocess.run(cmd, cwd=workspace_root, 
                              capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            print(f"⚠️ rust-analyzer error: {result.stderr}")
            return None, None, None
            
        data = json.loads(result.stdout)
        
        if "result" not in data or not data["result"]:
            return None, None, None
            
        target = data["result"]["target"]
        file_path = target["file_path"]
        
        # Extract crate and module path
        crate_name = target.get("crate_name")
        module_path = target.get("module_path", "")
        
        return file_path, crate_name, module_path
        
    except Exception as e:
        print(f"⚠️ Error querying rust-analyzer: {e}")
        return None, None, None

def find_correct_import_with_ra(workspace_root, struct_name, current_crate=None):
    """Find the correct import using rust-analyzer"""
    file_path, crate_name, module_path = query_rust_analyzer(workspace_root, struct_name)
    
    if not file_path:
        print(f"❌ rust-analyzer couldn't find `{struct_name}`")
        # Fall back to the original method
        return find_correct_import(workspace_root, struct_name, workspace_root, current_crate)
    
    print(f"✅ Found `{struct_name}` with rust-analyzer:")
    display_path = os.path.relpath(file_path, workspace_root) if workspace_root else file_path
    print(f"   - {display_path}")
    
    use_statements = []
    
    # Normalize crate name
    if crate_name:
        normalized_crate = normalize_crate_name(crate_name)
        
        # Generate import statement
        if current_crate and normalized_crate == normalize_crate_name(current_crate):
            # Same crate
            if module_path:
                module_parts = module_path.split("::")
                module_parts = [p for p in module_parts if p and p != "crate"]
                if module_parts:
                    import_path = f"use crate::{'/'.join(module_parts)}::{struct_name};"
                else:
                    import_path = f"use crate::{struct_name};"
            else:
                import_path = f"use crate::{struct_name};"
                
            use_statements.append((import_path, "from rust-analyzer (same crate)"))
        else:
            # Different crate
            if module_path:
                # Remove the crate prefix if present in the module path
                if module_path.startswith(f"{normalized_crate}::"):
                    module_path = module_path[len(f"{normalized_crate}::"):]
                    
                module_parts = module_path.split("::")
                module_parts = [p for p in module_parts if p and p != "crate"]
                
                if module_parts:
                    import_path = f"use {normalized_crate}::{'/'.join(module_parts)}::{struct_name};"
                else:
                    import_path = f"use {normalized_crate}::{struct_name};"
            else:
                import_path = f"use {normalized_crate}::{struct_name};"
                
            use_statements.append((import_path, "from rust-analyzer (external crate)"))
    
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

    # Check if rust-analyzer is available
    use_rust_analyzer = check_rust_analyzer_installed()
    
    print(f"📦 Workspace root: {workspace_root}")
    print(f"🔍 Searching for `{struct_name}`...\n")
    
    if use_rust_analyzer:
        print("🔧 Using rust-analyzer for accurate results")
        use_statements = find_correct_import_with_ra(str(workspace_root), struct_name, crate_name)
    else:
        print("⚠️ rust-analyzer not found. Using fallback method.")
        use_statements = find_correct_import(str(workspace_root), struct_name, workspace_root, crate_name)

    if use_statements:
        print("\n🎯 Suggested `use` statements:")
        for stmt, note in use_statements:
            print(f"   {stmt}   // {note}")
