#!/usr/bin/env python3
"""
Find Files Utility

A Typer-based command line utility to find books and movies in external drives.
"""

import os
import typer
from pathlib import Path
from typing import List, Optional
import fnmatch
import subprocess
from datetime import datetime

app = typer.Typer(help="Find files in external drives")

# Default search directories
DEFAULT_BOOK_FOLDERS = [
    '/Volumes/F/Books',
    '/Volumes/H-WD/books',
    '/Users/kosiew/Downloads/Movies/books'
]

DEFAULT_MOVIE_FOLDERS = [
    "/Volumes/G-WD/Movies",
    "/Volumes/G-WD/Movies-big",
    "/Volumes/H-WD/Movies",
    "/Volumes/F/Movies",
    "/Users/kosiew/Downloads/Movies"
]

# File extensions to search for
BOOK_EXTENSIONS = ['*.pdf', '*.epub', '*.mobi', '*.azw', '*.azw3', '*.djvu', '*.txt', '*.doc', '*.docx']
MOVIE_EXTENSIONS = ['*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv', '*.flv', '*.webm', '*.m4v', '*.mpg', '*.mpeg']


def search_files(search_term: str, folders: List[str], extensions: List[str]) -> List[Path]:
    """
    Search for files matching the search term in specified folders.
    
    Args:
        search_term: The string to search for in filenames
        folders: List of folder paths to search in
        extensions: List of file extensions to include in search
        
    Returns:
        List of matching file paths
    """
    found_files = []
    search_term_lower = search_term.lower()
    
    for folder in folders:
        folder_path = Path(folder)
        if not folder_path.exists():
            typer.echo(f"⚠️  Skipping (not found): {folder}", err=True)
            continue
            
        typer.echo(f"🔍 Searching in: {folder}")
        
        try:
            # Walk through all subdirectories
            for root, dirs, files in os.walk(folder_path):
                for filename in files:
                    filename_lower = filename.lower()
                    
                    # Check if filename contains search term
                    if search_term_lower in filename_lower:
                        # Check if file has one of the desired extensions
                        for ext_pattern in extensions:
                            if fnmatch.fnmatch(filename_lower, ext_pattern.lower()):
                                file_path = Path(root) / filename
                                found_files.append(file_path)
                                break
        except PermissionError:
            typer.echo(f"Permission denied: {folder}", err=True)
        except Exception as e:
            typer.echo(f"Error searching {folder}: {e}", err=True)
    
    return found_files


def display_results(files: List[Path], search_term: str, file_type: str):
    """Display search results in a formatted way."""
    if not files:
        typer.echo(f"No {file_type} found matching '{search_term}'")
        return
    
    typer.echo(f"\nFound {len(files)} {file_type}(s) matching '{search_term}':")
    typer.echo("=" * 60)
    
    for i, file_path in enumerate(files, 1):
        # Get file size
        try:
            size = file_path.stat().st_size
            size_mb = size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB"
        except:
            size_str = "Unknown size"
        
        typer.echo(f"{i:3d}. {file_path.name}")
        typer.echo(f"     Path: {file_path.parent}")
        typer.echo(f"     Size: {size_str}")
        typer.echo()


@app.command()
def books(
    search_term: str = typer.Argument(..., help="Search term to look for in book filenames"),
    folders: Optional[List[str]] = typer.Option(None, "--folder", "-f", help="Additional folders to search"),
    case_sensitive: bool = typer.Option(False, "--case-sensitive", "-c", help="Enable case-sensitive search")
):
    """
    Find books matching the search term in default book folders.
    """
    search_folders = DEFAULT_BOOK_FOLDERS.copy()
    if folders:
        search_folders.extend(folders)
    
    typer.echo(f"Searching for books containing: '{search_term}'")
    
    found_files = search_files(search_term, search_folders, BOOK_EXTENSIONS)
    display_results(found_files, search_term, "book")


@app.command()
def movies(
    search_term: str = typer.Argument(..., help="Search term to look for in movie filenames"),
    folders: Optional[List[str]] = typer.Option(None, "--folder", "-f", help="Additional folders to search"),
    case_sensitive: bool = typer.Option(False, "--case-sensitive", "-c", help="Enable case-sensitive search")
):
    """
    Find movies matching the search term in default movie folders.
    """
    search_folders = DEFAULT_MOVIE_FOLDERS.copy()
    if folders:
        search_folders.extend(folders)
    
    typer.echo(f"Searching for movies containing: '{search_term}'")
    
    found_files = search_files(search_term, search_folders, MOVIE_EXTENSIONS)
    display_results(found_files, search_term, "movie")


@app.command()
def list_folders():
    """
    List all configured search folders for books and movies.
    """
    typer.echo("Default Book Folders:")
    typer.echo("=" * 30)
    for folder in DEFAULT_BOOK_FOLDERS:
        exists = "✓" if Path(folder).exists() else "✗"
        typer.echo(f"{exists} {folder}")
    
    typer.echo("\nDefault Movie Folders:")
    typer.echo("=" * 30)
    for folder in DEFAULT_MOVIE_FOLDERS:
        exists = "✓" if Path(folder).exists() else "✗"
        typer.echo(f"{exists} {folder}")


@app.command()
def extensions():
    """
    List supported file extensions for books and movies.
    """
    typer.echo("Supported Book Extensions:")
    typer.echo("=" * 30)
    for ext in BOOK_EXTENSIONS:
        typer.echo(f"  {ext}")
    
    typer.echo("\nSupported Movie Extensions:")
    typer.echo("=" * 30)
    for ext in MOVIE_EXTENSIONS:
        typer.echo(f"  {ext}")


def parse_and_validate_datetime(date_time: str) -> datetime:
    """
    Parse and validate a datetime string in YYYYMMDDhhmm.ss format.
    
    Args:
        date_time: Date string in YYYYMMDDhhmm.ss format
        
    Returns:
        Validated datetime object
        
    Raises:
        typer.Exit: If date format is invalid
    """
    try:
        # Parse the date format YYYYMMDDhhmm.ss
        if '.' in date_time:
            date_part, seconds = date_time.split('.')
            if len(date_part) != 12 or len(seconds) != 2:
                raise ValueError("Invalid format")
        else:
            date_part = date_time
            seconds = "00"
            if len(date_part) != 12:
                raise ValueError("Invalid format")
        
        # Validate that it's a valid date
        year = int(date_part[0:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(date_part[8:10])
        minute = int(date_part[10:12])
        second = int(seconds)
        
        # Create datetime object to validate
        return datetime(year, month, day, hour, minute, second)
        
    except (ValueError, IndexError):
        typer.echo(f"❌ Error: Invalid date format '{date_time}'. Expected: YYYYMMDDhhmm.ss", err=True)
        typer.echo("Example: 202312251430.45 (December 25, 2023, 2:30:45 PM)", err=True)
        raise typer.Exit(1)


def collect_paths_for_touching(paths: List[str], recursive: bool) -> List[Path]:
    """
    Collect all file and directory paths to be touched based on input paths and options.
    
    Args:
        paths: List of path strings to process
        recursive: Whether to recursively process directories
        
    Returns:
        List of Path objects to touch
    """
    items_to_touch = []
    
    for path_str in paths:
        path = Path(path_str)
        
        if not path.exists():
            typer.echo(f"⚠️  Path not found: {path}", err=True)
            continue
        
        if path.is_file():
            items_to_touch.append(path)
        elif path.is_dir():
            items_to_touch.extend(_collect_directory_items(path, recursive))
    
    return items_to_touch


def _collect_directory_items(directory: Path, recursive: bool) -> List[Path]:
    """
    Collect items from a directory for touching.
    
    Args:
        directory: Directory path to process
        recursive: Whether to include subdirectories
        
    Returns:
        List of Path objects from the directory
    """
    items = []
    
    if recursive:
        # Walk through all subdirectories
        for root, dirs, files in os.walk(directory):
            # Add the current directory
            items.append(Path(root))
            # Add all files in current directory
            for filename in files:
                items.append(Path(root) / filename)
    else:
        # Add the folder itself
        items.append(directory)
        # Add only files directly in the folder
        for item in directory.iterdir():
            if item.is_file():
                items.append(item)
    
    return items


def display_touch_summary(target_datetime: Optional[datetime], items_count: int):
    """
    Display summary information about the touch operation.
    
    Args:
        target_datetime: Target datetime or None for current time
        items_count: Number of items to be touched
    """
    if target_datetime:
        typer.echo(f"📅 Target date/time: {target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        typer.echo("📅 Target date/time: Current time")
    
    typer.echo(f"📊 Found {items_count} items to touch")


def show_dry_run_preview(items_to_touch: List[Path]):
    """
    Display a preview of items that would be touched in dry run mode.
    
    Args:
        items_to_touch: List of paths that would be touched
    """
    typer.echo("\n🔍 DRY RUN - Would touch these items:")
    for item in items_to_touch[:10]:  # Show first 10 items
        typer.echo(f"  {item}")
    if len(items_to_touch) > 10:
        typer.echo(f"  ... and {len(items_to_touch) - 10} more items")


def confirm_touch_operation(items_count: int) -> bool:
    """
    Ask for user confirmation before proceeding with large touch operations.
    
    Args:
        items_count: Number of items to be touched
        
    Returns:
        True if user confirms, False otherwise
    """
    if items_count > 10:
        return typer.confirm(f"\nProceed to touch {items_count} items?")
    return True


def build_touch_command(date_time: Optional[str], access_time: bool, modification_time: bool, file_path: str) -> List[str]:
    """
    Build the touch command arguments based on options.
    
    Args:
        date_time: Date string or None
        access_time: Whether to change access time only
        modification_time: Whether to change modification time only
        file_path: Path to the file to touch
        
    Returns:
        List of command arguments
    """
    cmd = ["touch"]
    
    if access_time:
        cmd.append("-a")
    if modification_time:
        cmd.append("-m")
    if date_time:
        cmd.extend(["-t", date_time.replace('.', '')])
    
    cmd.append(file_path)
    return cmd


def execute_touch_operations(items_to_touch: List[Path], date_time: Optional[str], 
                           access_time: bool, modification_time: bool) -> tuple[int, int]:
    """
    Execute touch operations on all items and track progress.
    
    Args:
        items_to_touch: List of paths to touch
        date_time: Date string or None
        access_time: Whether to change access time only
        modification_time: Whether to change modification time only
        
    Returns:
        Tuple of (success_count, error_count)
    """
    success_count = 0
    error_count = 0
    total_items = len(items_to_touch)
    
    typer.echo(f"\n🔄 Processing {total_items} items...")
    
    for item in items_to_touch:
        try:
            cmd = build_touch_command(date_time, access_time, modification_time, str(item))
            subprocess.run(cmd, check=True, capture_output=True)
            success_count += 1
            
            # Show progress every 100 files or for small operations
            if success_count % 100 == 0:
                typer.echo(f"   Processed {success_count}/{total_items} items...")
            elif total_items <= 10:
                typer.echo(f"✅ Timestamps updated: {item}")
                
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Error touching {item}: {e}", err=True)
            error_count += 1
        except Exception as e:
            typer.echo(f"❌ Unexpected error with {item}: {e}", err=True)
            error_count += 1
    
    return success_count, error_count


def display_touch_results(success_count: int, error_count: int):
    """
    Display the final results of the touch operation.
    
    Args:
        success_count: Number of successfully touched items
        error_count: Number of items that failed
    """
    typer.echo(f"\n✅ Touch operation completed!")
    typer.echo(f"   Successfully touched: {success_count} items")
    if error_count > 0:
        typer.echo(f"   Errors: {error_count} items")


@app.command()
def touch(
    paths: List[str] = typer.Argument(..., help="List of files or folders to update timestamps for"),
    date_time: Optional[str] = typer.Option(None, "--date", "-d", help="Date and time in YYYYMMDDhhmm.ss format (e.g., 202312251430.45)"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Touch files recursively in subdirectories for folders"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be done without actually doing it"),
    access_time: bool = typer.Option(False, "--atime", help="Change access time only"),
    modification_time: bool = typer.Option(False, "--mtime", help="Change modification time only")
):
    """
    Update the timestamps of files or folders.
    
    Can handle both individual files and folders. For folders, use --recursive to touch all contents.
    Use --date to set a specific timestamp in YYYYMMDDhhmm.ss format.
    """
    # Validate date format if provided
    target_datetime = None
    if date_time:
        target_datetime = parse_and_validate_datetime(date_time)
    
    # Collect all items to touch
    items_to_touch = collect_paths_for_touching(paths, recursive)
    
    if not items_to_touch:
        typer.echo("❌ No valid files or folders found to touch")
        raise typer.Exit(1)
    
    # Display summary
    display_touch_summary(target_datetime, len(items_to_touch))
    
    if dry_run:
        show_dry_run_preview(items_to_touch)
        return
    
    # Confirm before proceeding if many items
    if not confirm_touch_operation(len(items_to_touch)):
        typer.echo("❌ Operation cancelled")
        raise typer.Exit(0)
    
    # Execute touch operations
    success_count, error_count = execute_touch_operations(
        items_to_touch, date_time, access_time, modification_time
    )
    
    # Display results
    display_touch_results(success_count, error_count)


if __name__ == "__main__":
    app()