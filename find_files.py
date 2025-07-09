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
import shutil
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
SUBTITLE_EXTENSIONS = ['*.srt', '*.sub', '*.idx', '*.ass', '*.ssa', '*.vtt']


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
    List supported file extensions for books, movies, and subtitles.
    """
    typer.echo("Supported Book Extensions:")
    typer.echo("=" * 30)
    for ext in BOOK_EXTENSIONS:
        typer.echo(f"  {ext}")
    
    typer.echo("\nSupported Movie Extensions:")
    typer.echo("=" * 30)
    for ext in MOVIE_EXTENSIONS:
        typer.echo(f"  {ext}")
    
    typer.echo("\nSupported Subtitle Extensions:")
    typer.echo("=" * 30)
    for ext in SUBTITLE_EXTENSIONS:
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
        # Format for touch: [[CC]YY]MMDDhhmm[.SS]
        # If there are seconds, keep the dot; if not, just use the date part
        if '.' in date_time:
            # Keep the original format with dot for seconds
            cmd.extend(["-t", date_time])
        else:
            # No seconds, use as-is
            cmd.extend(["-t", date_time])
    
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
        cmd = None
        try:
            cmd = build_touch_command(date_time, access_time, modification_time, str(item))
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            success_count += 1
            
            # Show progress every 100 files or for small operations
            if success_count % 100 == 0:
                typer.echo(f"   Processed {success_count}/{total_items} items...")
            elif total_items <= 10:
                typer.echo(f"✅ Timestamps updated: {item}")
                
        except subprocess.CalledProcessError as e:
            # Capture detailed error information
            stderr_output = e.stderr.strip() if e.stderr else "No error details available"
            stdout_output = e.stdout.strip() if e.stdout else ""
            
            typer.echo(f"❌ Error touching {item}:", err=True)
            typer.echo(f"   Command: {' '.join(cmd) if cmd else 'Command not available'}", err=True)
            typer.echo(f"   Exit code: {e.returncode}", err=True)
            if stderr_output:
                typer.echo(f"   Error output: {stderr_output}", err=True)
            if stdout_output:
                typer.echo(f"   Standard output: {stdout_output}", err=True)
            
            error_count += 1
        except Exception as e:
            typer.echo(f"❌ Unexpected error with {item}: {e}", err=True)
            typer.echo(f"   Command attempted: {' '.join(cmd) if cmd else 'Command not built'}", err=True)
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


def find_matching_movie_folder(subtitle_name: str, movie_folders: List[str]) -> Optional[Path]:
    """
    Find a matching movie folder based on subtitle filename.
    
    Args:
        subtitle_name: Name of the subtitle file (without extension)
        movie_folders: List of movie folder paths to search in
        
    Returns:
        Path to matching movie folder or None if not found
    """
    subtitle_name_lower = subtitle_name.lower()
    
    for movie_folder in movie_folders:
        movie_folder_path = Path(movie_folder)
        if not movie_folder_path.exists():
            continue
            
        try:
            for root, dirs, files in os.walk(movie_folder_path):
                # Check for matching movie files in current directory
                for filename in files:
                    filename_lower = filename.lower()
                    file_stem = Path(filename).stem.lower()
                    
                    # Check if it's a movie file and matches the subtitle name
                    for ext_pattern in MOVIE_EXTENSIONS:
                        if fnmatch.fnmatch(filename_lower, ext_pattern.lower()):
                            # Simple matching: check if subtitle name is in movie name or vice versa
                            if (subtitle_name_lower in file_stem or 
                                file_stem in subtitle_name_lower or
                                _fuzzy_match(subtitle_name_lower, file_stem)):
                                return Path(root)
        except (PermissionError, Exception):
            continue
    
    return None


def _fuzzy_match(subtitle_name: str, movie_name: str, threshold: float = 0.7) -> bool:
    """
    Perform fuzzy matching between subtitle and movie names.
    
    Args:
        subtitle_name: Subtitle filename (lowercase, no extension)
        movie_name: Movie filename (lowercase, no extension)
        threshold: Similarity threshold (0.0 to 1.0)
        
    Returns:
        True if names are similar enough
    """
    # Remove common words and characters that might differ
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    def clean_name(name: str) -> str:
        # Replace common separators with spaces
        name = name.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        # Remove year patterns like (2023) or [2023]
        import re
        name = re.sub(r'[\(\[]?\d{4}[\)\]]?', '', name)
        # Split into words and remove common words
        words = [word for word in name.split() if word not in common_words and len(word) > 2]
        return ' '.join(words)
    
    clean_subtitle = clean_name(subtitle_name)
    clean_movie = clean_name(movie_name)
    
    # Simple word overlap check
    subtitle_words = set(clean_subtitle.split())
    movie_words = set(clean_movie.split())
    
    if not subtitle_words or not movie_words:
        return False
    
    # Calculate Jaccard similarity
    intersection = len(subtitle_words & movie_words)
    union = len(subtitle_words | movie_words)
    
    return (intersection / union) >= threshold if union > 0 else False


def copy_subtitle_files(source_folders: List[str], target_folders: List[str], dry_run: bool = False) -> tuple[int, int, int]:
    """
    Copy subtitle files from source folders to matching movie folders.
    
    Args:
        source_folders: List of folders containing subtitle files
        target_folders: List of movie folders to search for matches
        dry_run: If True, only show what would be copied
        
    Returns:
        Tuple of (copied_count, skipped_count, error_count)
    """
    copied_count = 0
    skipped_count = 0
    error_count = 0
    
    for source_folder in source_folders:
        source_path = Path(source_folder)
        if not source_path.exists():
            typer.echo(f"⚠️  Source folder not found: {source_folder}", err=True)
            continue
            
        typer.echo(f"🔍 Searching for subtitles in: {source_folder}")
        
        try:
            # Find all subtitle files in source folder
            for root, dirs, files in os.walk(source_path):
                for filename in files:
                    filename_lower = filename.lower()
                    
                    # Check if it's a subtitle file
                    is_subtitle = any(fnmatch.fnmatch(filename_lower, ext.lower()) 
                                    for ext in SUBTITLE_EXTENSIONS)
                    
                    if not is_subtitle:
                        continue
                    
                    subtitle_path = Path(root) / filename
                    subtitle_stem = subtitle_path.stem
                    
                    # Find matching movie folder
                    matching_folder = find_matching_movie_folder(subtitle_stem, target_folders)
                    
                    if matching_folder:
                        target_path = matching_folder / filename
                        
                        if target_path.exists():
                            typer.echo(f"⏭️  Skipping (already exists): {filename} -> {matching_folder}")
                            skipped_count += 1
                            continue
                        
                        if dry_run:
                            typer.echo(f"📋 Would copy: {subtitle_path} -> {target_path}")
                            copied_count += 1
                        else:
                            try:
                                shutil.copy2(subtitle_path, target_path)
                                typer.echo(f"✅ Copied: {filename} -> {matching_folder}")
                                copied_count += 1
                            except Exception as e:
                                typer.echo(f"❌ Error copying {filename}: {e}", err=True)
                                error_count += 1
                    else:
                        typer.echo(f"❓ No matching movie found for: {filename}")
                        skipped_count += 1
                        
        except PermissionError:
            typer.echo(f"Permission denied: {source_folder}", err=True)
            error_count += 1
        except Exception as e:
            typer.echo(f"Error processing {source_folder}: {e}", err=True)
            error_count += 1
    
    return copied_count, skipped_count, error_count


@app.command()
def copy_subtitles(
    source_folders: List[str] = typer.Argument(..., help="Source folders containing subtitle files"),
    target_folders: Optional[List[str]] = typer.Option(None, "--target", "-t", help="Target movie folders (defaults to DEFAULT_MOVIE_FOLDERS)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be copied without actually copying"),
    extensions: Optional[List[str]] = typer.Option(None, "--ext", help="Additional subtitle extensions to include")
):
    """
    Copy subtitle files from source folders to matching movie folders.
    
    Searches for .srt and other subtitle files in the specified source folders,
    then attempts to find matching movie folders in the target directories
    and copies the subtitle files there.
    """
    # Use default movie folders if none specified
    movie_folders = target_folders if target_folders else DEFAULT_MOVIE_FOLDERS.copy()
    
    # Add additional extensions if specified
    search_extensions = SUBTITLE_EXTENSIONS.copy()
    if extensions:
        search_extensions.extend([f"*.{ext.lstrip('*.')}" for ext in extensions])
    
    typer.echo(f"🎬 Copying subtitles from {len(source_folders)} source folder(s)")
    typer.echo(f"🎯 Searching in {len(movie_folders)} movie folder(s)")
    
    if dry_run:
        typer.echo("🔍 DRY RUN MODE - No files will be copied")
    
    typer.echo(f"📄 Looking for extensions: {', '.join(search_extensions)}")
    typer.echo()
    
    # Copy subtitle files
    copied_count, skipped_count, error_count = copy_subtitle_files(
        source_folders, movie_folders, dry_run
    )
    
    # Display results
    typer.echo("\n" + "=" * 60)
    typer.echo("📊 Copy Summary:")
    if dry_run:
        typer.echo(f"   Would copy: {copied_count} subtitle files")
    else:
        typer.echo(f"   Copied: {copied_count} subtitle files")
    typer.echo(f"   Skipped: {skipped_count} files")
    if error_count > 0:
        typer.echo(f"   Errors: {error_count} files")


# ...existing code...
if __name__ == "__main__":
    app()