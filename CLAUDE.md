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

## System Architecture

### Layered Design
- **Foundation Layer**: `zd.py` (debugging/logging), `u.py` (utilities), `aspect.py` (AOP/tracing)
- **Infrastructure Layer**: `bv_config.py` (configuration), `bv_file.py` (file operations)
- **Application Layer**: Domain-specific modules like `bv_bloomberg.py`, `bv_beautiful_soup.py`
- **CLI Layer**: Executable scripts like `open_urls.py`, `find_files.py`

### Core Dependencies
```
zd.py (logging/debugging)
├── aspect.py (AOP/tracing) → All modules
├── u.py (utilities) → bv_date.py, bv_time.py, bv_config.py
└── bv_config.py (configuration) → All application modules
```

### Module Categories
- **Core Utilities**: `u.py`, `zd.py`, `aspect.py`
- **Infrastructure**: `bv_config.py`, `bv_file.py`, `bv_yaml.py`
- **Domain Services**: `bv_bloomberg.py`, `bv_beautiful_soup.py`, `bv_speak.py`
- **Application Scripts**: `open_urls.py`, `find_files.py`, `delete_images.py`
- **Development Tools**: `rust_tools.py`, `critcmp.py`, `be_mail.py`

### Execution Patterns

**CLI Pattern (Fire-based):**
```python
@attr.s
class Runner(bv_fire._Runner):
    def command(self): ...
if __name__ == "__main__":
    bv_fire.Fire(Runner)
```

**Direct Execution:**
```python
if __name__ == "__main__":
    main()
```

**Test Pattern:**
```python
def _test():
    """repository of all tests"""
    import doctest
    doctest.testmod(...)
```

### Configuration Management
- **YAML**: `_zd.yml` for logging configuration (used by `zd.py`)
- **INI**: `_open_urls.ini` for application settings
- **Programmatic**: `Config` class in `bv_config.py`
- **Resolution Order**: Environment vars → local config files → CLI args

### Cross-Cutting Concerns
- **Logging**: Centralized via `zd.py` with YAML configuration
- **Tracing**: AOP-based via `aspect.wrap_module(__name__)`
- **Testing**: Docstring tests + module-level `_test()` functions
- **Error Handling**: Custom exception hierarchies with `zd.py` logging

### Dependencies
- **Testing**: `pytest` for framework tests, doctest for inline tests
- **Linting**: `ruff` for code quality and formatting
- **Common Libraries**: `attr`, `pyyaml`, `configparser`, `pathlib`, `fire`
- **Cross-References**: Custom modules import each other (e.g., `u.py` → `zd.py`)

### Development Guidelines
From `.github/copilot-instructions.md`:
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Keep functions focused and under ~25 lines
- Use descriptive function names
- Leverage Python idioms (list comprehensions, generators, context managers)
- Code must comply with Ruff lint rules

### Extension Points
- **URL Collections**: INI-based configuration in `open_urls.py`
- **Pattern Matching**: Regex and BeautifulSoup patterns in config files
- **Task Scheduling**: Day-of-week based collections (monday, tuesday, etc.)

## Quick Start
1. **Test a script**: `python3 script_name.py`
2. **Run all tests**: `python3 -m pytest`
3. **Check code**: `ruff check`
4. **Format code**: `ruff format`

# Summary instructions
When you are using compact, please focus on test output and code changes 
