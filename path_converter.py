import os
import pathlib

def get_relative_path(full_path, workspace_root):
    """
    Convert an absolute path to a path relative to the workspace root.
    
    Args:
        full_path (str): The absolute path to convert
        workspace_root (str): The absolute path to the workspace root
        
    Returns:
        str: The path relative to workspace root, or the original path if not under workspace_root
    """
    # Convert to Path objects to handle path operations consistently across platforms
    path = pathlib.Path(full_path)
    root = pathlib.Path(workspace_root)
    
    # Check if the path is inside the workspace root
    try:
        relative = path.relative_to(root)
        return str(relative)
    except ValueError:
        # Path is not under workspace_root
        return full_path

def convert_paths_in_text(text, workspace_root):
    """
    Replace all absolute paths that start with workspace_root with relative paths.
    
    Args:
        text (str): Text containing paths to convert
        workspace_root (str): The absolute path to the workspace root
        
    Returns:
        str: Text with converted paths
    """
    lines = text.split('\n')
    result = []
    
    for line in lines:
        if workspace_root in line:
            # Simple replacement strategy
            result.append(line.replace(workspace_root + '/', ''))
        else:
            result.append(line)
    
    return '\n'.join(result)


if __name__ == "__main__":
    # Example usage
    workspace_root = "/Users/kosiew/GitHub/datafusion"
    test_path = "/Users/kosiew/GitHub/datafusion/datafusion/datasource/src/url.rs"
    
    print(f"Original: {test_path}")
    print(f"Relative: {get_relative_path(test_path, workspace_root)}")
    
    # Example for text conversion
    sample_text = """
    📂 Current directory: /Users/kosiew/GitHub/datafusion/datafusion/datasource/src
    📦 Workspace root: /Users/kosiew/GitHub/datafusion
    🔍 Searching for `ListingTableUrl`...

    ✅ Found `ListingTableUrl` defined in:
       - /Users/kosiew/GitHub/datafusion/datafusion/datasource/src/url.rs
    """
    
    print("\nConverted text:")
    print(convert_paths_in_text(sample_text, workspace_root))
