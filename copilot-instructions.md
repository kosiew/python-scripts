# Copilot Code Generation Instructions

When generating code for this project, please follow these guidelines:

## General Guidelines
- Always add a comment: '==> Prompt improved'
- Ensure code is well-documented with clear comments
- Follow established patterns in the existing codebase
- Code must comply with Ruff lint rules

## Python-Specific Guidelines
- Write Python-idiomatic code following PEP 8 style guidelines
- Use list comprehensions, generators, and other Python idioms when appropriate
- Prefer Python's built-in functions and standard library solutions
- Follow Python naming conventions (snake_case for variables/functions, PascalCase for classes)
- Use type hints for function parameters and return values
- Leverage context managers (with statements) for resource handling
- Use classes to organize code where possible, following object-oriented design principles
- Look for opportunities for code reuse before adding new code, but adhere to good sense and don't overengineer

## Code Structure
- Avoid overly long functions by breaking them into smaller, focused functions
- Each function should do one thing well (Single Responsibility Principle)
- Limit function length to ~25 lines where possible
- Extract repeated logic into separate helper functions
- Use descriptive function names that indicate their purpose
