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


if __name__ == "__main__":
    app()