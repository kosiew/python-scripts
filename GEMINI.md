# Gemini Guidelines for `python-scripts`

This repository is a collection of personal Python scripts. The user is the primary author.

## General Approach

- **Style:** The coding style may be inconsistent across different scripts. When modifying a script, try to match the existing style within that file.
- **Simplicity:** These are utility scripts. Keep changes straightforward and focused on the user's request.
- **Testing:** When modifying an existing script, take the opportunity to add automated tests for the changes. Use the `pytest` framework. If a test file doesn't exist for the script, create one (e.g., `test_script_name.py`).
- **Dependencies:** Be mindful of introducing new dependencies. Check if the required library is already used in the project or is a standard Python library before adding it.

## Key Files

- `*.py`: The Python scripts themselves.
- `_*.yml`, `_*.ini`: These appear to be configuration files for the scripts (e.g., `_bv_bloomberg.yml`, `_open_urls.ini`). When a script is being modified, check for a corresponding configuration file.

## Development Workflow

- **Verification:** Before committing, ensure the script is executable and free of syntax errors.
- **Commits:** Write clear and concise commit messages that explain the "why" behind the change.
