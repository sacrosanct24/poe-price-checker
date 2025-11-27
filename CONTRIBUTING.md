# Contributing to PoE Price Checker

Thank you for your interest in contributing to PoE Price Checker! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior via GitHub Issues.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- A Path of Exile account (for testing features)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/exilePriceCheck.git
   cd exilePriceCheck
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/sacrosanct24/exilePriceCheck.git
   ```

## Development Setup

### Create a Virtual Environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### Run the Application

```bash
python -m gui_qt.main
```

### Run Tests

```bash
python -m pytest tests/ --ignore=tests/integration
```

## How to Contribute

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates.

When filing a bug report, include:
- **Clear title** describing the issue
- **Steps to reproduce** the behavior
- **Expected behavior** vs **actual behavior**
- **Screenshots** if applicable
- **Environment details**: OS, Python version, application version
- **Item text** (if related to item parsing) - redact any personal info

### Suggesting Features

We welcome feature suggestions! Please:
- Check existing issues and discussions first
- Clearly describe the feature and its use case
- Explain why this would benefit other users
- Consider implementation complexity

### Contributing Code

1. **Find or create an issue** for the work you want to do
2. **Comment on the issue** to let others know you're working on it
3. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** following our coding standards
5. **Write or update tests** for your changes
6. **Submit a pull request**

## Pull Request Process

### Before Submitting

1. **Update documentation** if needed
2. **Run the test suite** and ensure all tests pass:
   ```bash
   python -m pytest tests/ --ignore=tests/integration
   ```
3. **Run linting**:
   ```bash
   flake8 core/ gui_qt/ data_sources/
   ```
4. **Update CHANGELOG.md** with your changes under "Unreleased"

### PR Guidelines

- **One feature/fix per PR** - keep changes focused
- **Write a clear PR description** explaining:
  - What changes were made
  - Why the changes were needed
  - How to test the changes
- **Reference related issues** using `Fixes #123` or `Closes #123`
- **Keep commits atomic** and write meaningful commit messages

### Review Process

1. Maintainers will review your PR
2. Address any requested changes
3. Once approved, your PR will be merged

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Example

```python
def calculate_item_value(
    item: ParsedItem,
    price_source: PriceSource,
) -> Optional[float]:
    """
    Calculate the chaos value of an item.

    Args:
        item: The parsed item to evaluate
        price_source: Which pricing API to use

    Returns:
        The chaos value, or None if pricing failed
    """
    if not item.base_type:
        return None

    # Implementation...
    return value
```

### Import Order

1. Standard library imports
2. Third-party imports
3. Local imports

Separate each group with a blank line.

### Project Structure

```
exilePriceCheck/
├── core/               # Business logic (no GUI dependencies)
├── data_sources/       # API clients and data fetching
├── gui_qt/             # PyQt6 UI components
│   ├── dialogs/        # Modal dialogs
│   ├── widgets/        # Reusable widgets
│   └── windows/        # Main windows
├── tests/              # Test files
└── docs/               # Documentation
```

### Guidelines

- Keep UI and business logic separate
- Use dependency injection where possible
- Prefer composition over inheritance
- Handle exceptions at appropriate levels
- Log errors, don't swallow them silently

## Testing

### Test Structure

- Place tests in `tests/` directory
- Name test files `test_<module>.py`
- Name test functions `test_<what_is_being_tested>`

### Running Tests

```bash
# Run all tests
python -m pytest tests/ --ignore=tests/integration

# Run with coverage
python -m pytest tests/ --cov=core --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_item_parser.py -v

# Run tests matching a pattern
python -m pytest -k "test_parse" -v
```

### Writing Tests

- Test one thing per test function
- Use descriptive test names
- Include edge cases and error conditions
- Mock external dependencies (APIs, file system)

Example:
```python
def test_parse_rare_item_with_life_mod():
    """Test that life mods are correctly parsed from rare items."""
    parser = ItemParser()
    item_text = """
    Rarity: Rare
    Test Ring
    Coral Ring
    --------
    +50 to maximum Life
    """

    result = parser.parse(item_text)

    assert result is not None
    assert result.rarity == "Rare"
    assert any("Life" in mod for mod in result.explicit_mods)
```

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of function.

    Longer description if needed, explaining behavior,
    edge cases, or important details.

    Args:
        param1: Description of first parameter
        param2: Description of second parameter

    Returns:
        Description of return value

    Raises:
        ValueError: When param2 is negative
    """
```

### README Updates

If your changes affect:
- Installation process
- Usage instructions
- Configuration options
- Features list

Please update the README.md accordingly.

## Questions?

If you have questions about contributing:
- Check existing [GitHub Issues](https://github.com/sacrosanct24/exilePriceCheck/issues)
- Create a new issue with the "question" label
- Review the documentation in the `docs/` folder

Thank you for contributing!
