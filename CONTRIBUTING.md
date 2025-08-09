# Contributing to BOT Trading v3

First off, thank you for considering contributing to BOT Trading v3! It's people like you that make BOT Trading v3 such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots and animated GIFs if possible**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and explain which behavior you expected to see instead**
* **Explain why this enhancement would be useful**

### Pull Requests

* Fill in the required template
* Do not include issue numbers in the PR title
* Include screenshots and animated GIFs in your pull request whenever possible
* Follow the Python styleguides
* Include thoughtfully-worded, well-structured tests
* Document new code
* End all files with a newline

## Development Process

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code lints
6. Issue that pull request!

## Styleguides

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

### Python Styleguide

All Python code must adhere to:

* [PEP 8](https://www.python.org/dev/peps/pep-0008/)
* Use type hints for all functions
* Format with `black`
* Check with `ruff`
* Verify types with `mypy`

Example:

```python
def calculate_position_size(
    balance: Decimal,
    risk_percentage: float,
    stop_loss_distance: Decimal
) -> Decimal:
    """Calculate position size based on risk parameters.

    Args:
        balance: Account balance
        risk_percentage: Risk per trade (e.g., 0.02 for 2%)
        stop_loss_distance: Distance to stop loss in price units

    Returns:
        Position size in base currency
    """
    risk_amount = balance * Decimal(str(risk_percentage))
    position_size = risk_amount / stop_loss_distance
    return position_size
```

### Documentation Styleguide

* Use [Google style](https://google.github.io/styleguide/pyguide.html) for docstrings
* Keep line length to 80 characters in documentation
* Use Markdown for all documentation files

## Testing

Before submitting a pull request:

```bash
# Run all tests
pytest tests/

# Check code formatting
black . --check
ruff check .

# Type checking
mypy . --ignore-missing-imports

# Check for secrets
git diff --staged | grep -i "api_key\|secret\|password"
```

## Questions?

Feel free to open an issue with your question or contact the maintainers directly.

Thank you for contributing! 🎉
