# 🛡️ Code Quality & Automated Checks Guide

## Overview

This document describes the automated code quality checks implemented for BOT_AI_V3 project. The system ensures code quality, security, and consistency through pre-commit hooks and GitHub Actions CI/CD pipeline.

## 🚀 Quick Start

### Initial Setup

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Run setup script
./scripts/setup_pre_commit.sh

# 3. Install pre-commit hooks
pre-commit install
```

### Before Each Commit

The pre-commit hooks will run automatically. To run checks manually:

```bash
# Quick check (staged files only)
python scripts/pre_commit_check.py

# Full check (all files)
./scripts/run_checks.sh

# With tests
./scripts/run_checks.sh --with-tests
```

## 📋 Automated Checks

### 1. Secret Detection 🔐

- **Tool**: detect-secrets, custom script, TruffleHog
- **Checks for**: API keys, passwords, tokens, private keys
- **Config**: `.gitleaks.toml`, `.secrets.baseline`
- **Manual run**: `python scripts/check_secrets.py`

### 2. Code Formatting 🎨

- **Tool**: Black
- **Line length**: 100 characters
- **Config**: `pyproject.toml`
- **Fix**: `black . --line-length=100`

### 3. Import Sorting 📦

- **Tool**: isort
- **Profile**: black-compatible
- **Config**: `pyproject.toml`
- **Fix**: `isort . --profile black --line-length 100`

### 4. Linting 🔍

- **Tool**: Ruff (fast Python linter)
- **Rules**: E, W, F, I, B, C4, UP, ARG, SIM, TCH, DTZ, RUF, ASYNC, S
- **Config**: `pyproject.toml`
- **Fix**: `ruff check --fix .`

### 5. Type Checking 📝

- **Tool**: MyPy
- **Python version**: 3.12
- **Config**: `pyproject.toml`
- **Run**: `mypy . --ignore-missing-imports`

### 6. Security Scanning 🛡️

- **Tools**: Bandit, Semgrep, Safety
- **Config**: `pyproject.toml`
- **Run**: `bandit -r . --skip B101,B601`

### 7. Test Coverage 🧪

- **Tool**: pytest + coverage
- **Minimum coverage**: 80% for new code
- **Run**: `pytest tests/unit/ --cov=. --cov-report=term-missing`

## 🔄 GitHub Actions CI/CD

### Workflows

1. **CI Pipeline** (`.github/workflows/ci.yml`)
   - Runs on: push to main/develop, pull requests
   - Jobs: pre-commit, security, secrets, lint, test, quality

2. **Test Workflow** (`.github/workflows/test.yml`)
   - Matrix testing: Python 3.10, 3.11, 3.12
   - Services: PostgreSQL (port 5555), Redis

### Pipeline Steps

```yaml
jobs:
  - pre-commit        # All pre-commit hooks
  - security-scan     # Bandit, Safety, Semgrep
  - secrets-scan      # TruffleHog
  - lint-and-format   # Black, Ruff, MyPy
  - test             # Unit & integration tests
  - dependency-check  # Outdated packages, licenses
  - code-quality     # Complexity metrics
```

## 🛠️ Configuration Files

| File | Purpose |
|------|---------|
| `.pre-commit-config.yaml` | Pre-commit hooks configuration |
| `pyproject.toml` | Python tools configuration (Black, Ruff, MyPy, pytest) |
| `.gitleaks.toml` | Secret detection patterns |
| `.secrets.baseline` | Known secrets baseline |
| `.github/workflows/ci.yml` | Main CI/CD pipeline |

## 📊 Quality Metrics

### Code Complexity

- **Cyclomatic Complexity**: Max B (11-20)
- **Maintainability Index**: Min A (20-100)
- **Tool**: `radon cc . -s -nb`

### Security Score

- **Bandit**: No high severity issues
- **Safety**: No known vulnerabilities
- **Semgrep**: Auto-fix enabled

## 🔧 Local Development

### VSCode Settings

Add to `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=100"],
  "editor.formatOnSave": true,
  "python.linting.mypyEnabled": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### PyCharm Settings

1. **Black**: Settings → Tools → External Tools → Add Black
2. **Ruff**: Settings → Tools → External Tools → Add Ruff
3. **File Watchers**: Auto-format on save

## 🚨 Troubleshooting

### Pre-commit Fails

```bash
# Reset and reinstall
pre-commit uninstall
pre-commit clean
pre-commit install
pre-commit run --all-files
```

### Large Files Warning

```bash
# Use Git LFS for large files
git lfs track "*.pkl"
git lfs track "*.h5"
git add .gitattributes
```

### Secret Detected

```bash
# Remove from history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch PATH_TO_FILE" \
  --prune-empty --tag-name-filter cat -- --all
```

## 📈 Best Practices

1. **Always activate venv**: `source venv/bin/activate`
2. **Run checks before push**: `./scripts/run_checks.sh`
3. **Keep dependencies updated**: `pip list --outdated`
4. **Write tests for new code**: Min 80% coverage
5. **Use type hints**: For all public functions
6. **Document complex logic**: Clear docstrings
7. **No secrets in code**: Use `.env` files

## 🎯 Commit Message Format

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:

```
feat(trading): add ML-based signal filtering

- Implemented UnifiedPatchTST model integration
- Added 240+ technical indicators
- Optimized for <20ms inference

Closes #123
```

## 📝 Exemptions

To skip specific checks:

```python
# Skip specific line
result = eval(user_input)  # noqa: S307

# Skip file
# flake8: noqa

# Skip MyPy
# type: ignore

# Allow secret (false positive)
API_KEY = "example_key"  # pragma: allowlist secret
```

## 🔗 Resources

- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pre-commit Hooks](https://pre-commit.com/hooks.html)
- [GitHub Actions](https://docs.github.com/en/actions)

## 📞 Support

For issues with code quality tools:

1. Check this documentation
2. Run `./scripts/setup_pre_commit.sh` to reinstall
3. Create issue in GitHub with error logs
4. Contact team lead for assistance

---

**Remember**: Good code quality is not just about passing checks - it's about writing maintainable, secure, and efficient code that your team can work with confidently! 🚀
