# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
- `python3 -m pytest` - Run all tests using pytest framework
- `python3 script_name.py` - Run individual scripts (most have built-in test methods)
- Individual scripts can be tested by running them directly with `python3 script_name.py`

### Linting
- `ruff check` - Check for code quality issues with Ruff
- `ruff format` - Format code with Ruff

### Running Scripts
- Scripts are designed to be run directly: `python3 script_name.py`
- Many scripts use the `bv_fire` module (Fire CLI) for command-line interfaces
- Configuration files (`.yml`, `.ini`) are typically prefixed with `_` (e.g., `_zd.yml`, `_open_urls.ini`)

## Code Architecture

### Core Utility Modules
- `u.py` - General utility functions collection
- `zd.py` - Debugging utilities with YAML-based logging configuration
- `aspect.py` - Aspect-oriented programming utilities for tracing and debugging
- `bv_config.py` - Configuration file management using `configparser`
- `bv_file.py` - File operations, including classes for file manipulation tasks
- `bv_*.py` - Various utility modules (date, time, YAML, speak, etc.)

### Script Categories
- **File Management**: `delete_images.py`, `find_files.py`, `bv_file.py`
- **Web/Data Processing**: `bv_bloomberg.py`, `bv_beautiful_soup.py`, `open_urls.py`
- **Development Tools**: `rust_tools.py` (Rust workspace analysis), `critcmp.py`
- **Communication**: `be_mail.py`
- **General Utilities**: `u.py`, `zd.py`, `aspect.py`

### Key Patterns
- Most modules follow the pattern of having a `_test()` function for doctests
- Scripts use the `aspect.wrap_module(__name__)` pattern for debugging/tracing
- Configuration is managed through `.yml` and `.ini` files
- Many scripts include `bv_fire.Fire(Runner)` for CLI functionality with a `Runner` class

### Dependencies
- Uses `pytest` for testing (though some scripts have built-in doctests)
- `ruff` for linting and formatting
- Common libraries: `typer`, `attr`, `pyyaml`, `configparser`, `pathlib`
- Custom modules cross-reference each other (e.g., `u.py` imports `zd.py`)

### Development Guidelines
From `.github/copilot-instructions.md`:
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Keep functions focused and under ~25 lines
- Use descriptive function names
- Leverage Python idioms (list comprehensions, generators, context managers)
- Code must comply with Ruff lint rules