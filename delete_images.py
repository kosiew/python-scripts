import os
import glob
from typing import Optional, List, Dict
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

try:
    import typer
except ImportError:
    print("Please install typer using: pip install typer")
    exit(1)

DEFAULT_FOLDER = Path("~/Downloads").expanduser()

app = typer.Typer(help="CLI tool to list and delete image files in a folder")

def get_image_files(folder_path: Path) -> list[Path]:
    """
    Get a list of all image files in the specified folder (non-recursive)
    """
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.ico')
    image_files = []
    
    # Check if folder exists
    if not folder_path.exists():
        typer.secho(f"Error: Folder '{folder_path}' does not exist!", fg=typer.colors.RED)
        raise typer.Exit(1)
    
    # Get all files with image extensions
    for ext in image_extensions:
        image_files.extend(folder_path.glob(f'*{ext}'))
        image_files.extend(folder_path.glob(f'*{ext.upper()}'))
    
    return image_files

def get_age_bucket(file_path: Path) -> str:
    """Determine the age bucket for a file based on its modification time"""
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    now = datetime.now()
    
    if mtime.date() == now.date():
        return "Today"
    elif mtime > now - timedelta(days=7):
        return "Last 7 days"
    elif mtime > now - timedelta(days=30):
        return "Last 30 days"
    else:
        return "Older than 30 days"

class AgeBucket(str, Enum):
    TODAY = "today"
    LAST_7_DAYS = "last-7-days"
    LAST_30_DAYS = "last-30-days"
    OLDER = "older-than-30-days"
    ALL = "all"

def get_files_by_bucket(image_files: List[Path]) -> Dict[str, List[Path]]:
    """Group files by age bucket"""
    files_by_age: Dict[str, List[Path]] = {
        "Today": [],
        "Last 7 days": [],
        "Last 30 days": [],
        "Older than 30 days": []
    }
    
    for file in image_files:
        bucket = get_age_bucket(file)
        files_by_age[bucket].append(file)
    
    return files_by_age

@app.command()
def list(
    folder_path: Path = typer.Argument(DEFAULT_FOLDER, help="Path to the folder containing images", exists=True, file_okay=False, dir_okay=True)
):
    """List all image files in the specified folder (non-recursive)"""
    image_files = get_image_files(folder_path)
    
    if not image_files:
        typer.secho("No image files found in the specified folder.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    
    # Initialize dictionary with empty lists for each bucket
    files_by_age = {
        "Today": [],
        "Last 7 days": [],
        "Last 30 days": [],
        "Older than 30 days": []
    }
    
    # Group files by age bucket
    for file in image_files:
        bucket = get_age_bucket(file)
        files_by_age[bucket].append(file)
    
    # Display files grouped by age bucket
    typer.secho("\nFound the following image files:", fg=typer.colors.GREEN)
    buckets = ["Today", "Last 7 days", "Last 30 days", "Older than 30 days"]
    for bucket in buckets:
        if files_by_age[bucket]:  # Only show buckets that have files
            typer.secho(f"\n{bucket}:", fg=typer.colors.BLUE)
            for file in files_by_age[bucket]:
                typer.echo(f"- {file.name}")
    
    # Display summary
    typer.secho("\nSummary:", fg=typer.colors.GREEN)
    total_files = 0
    for bucket in buckets:
        count = len(files_by_age[bucket])
        total_files += count
        if count > 0:
            typer.echo(f"{bucket}: {count} files")
    typer.echo(f"Total: {total_files} files")

@app.command()
def delete(
    folder_path: Path = typer.Argument(DEFAULT_FOLDER, help="Path to the folder containing images", exists=True, file_okay=False, dir_okay=True),
    bucket: AgeBucket = typer.Option(
        AgeBucket.ALL,
        "--bucket", "-b",
        help="Age bucket of files to delete"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Delete without confirmation")
):
    """Delete image files in the specified folder by age bucket"""
    image_files = get_image_files(folder_path)
    
    if not image_files:
        typer.secho("No image files found in the specified folder.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    
    files_by_age = get_files_by_bucket(image_files)
    
    # Determine which files to delete based on the bucket option
    files_to_delete = []
    if bucket == AgeBucket.ALL:
        files_to_delete = image_files
    else:
        bucket_map = {
            AgeBucket.TODAY: "Today",
            AgeBucket.LAST_7_DAYS: "Last 7 days",
            AgeBucket.LAST_30_DAYS: "Last 30 days",
            AgeBucket.OLDER: "Older than 30 days"
        }
        bucket_name = bucket_map[bucket]
        files_to_delete = files_by_age[bucket_name]
    
    if not files_to_delete:
        typer.secho(f"No files found in the '{bucket.value}' bucket.", fg=typer.colors.YELLOW)
        raise typer.Exit()
    
    # Display files that will be deleted
    typer.secho(f"\nFiles to delete ({len(files_to_delete)} files):", fg=typer.colors.GREEN)
    for file in files_to_delete:
        typer.echo(f"- {file.name}")
    
    # Ask for confirmation unless force flag is used
    if not force:
        delete_confirmed = typer.confirm("\nDo you want to delete these files?")
        if not delete_confirmed:
            typer.secho("\nOperation cancelled. No files were deleted.", fg=typer.colors.YELLOW)
            raise typer.Exit()
    
    # Delete the files
    deleted_count = 0
    for file in files_to_delete:
        try:
            file.unlink()
            typer.secho(f"Deleted: {file.name}", fg=typer.colors.GREEN)
            deleted_count += 1
        except Exception as e:
            typer.secho(f"Error deleting {file.name}: {str(e)}", fg=typer.colors.RED)
    
    typer.secho(f"\nSuccessfully deleted {deleted_count} files from the '{bucket.value}' bucket.", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()