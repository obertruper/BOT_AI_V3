#!/bin/bash

# Setup pre-commit hooks for the project

set -e

echo "🔧 Setting up pre-commit hooks for BOT_AI_V3..."

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Activating virtual environment..."
    source venv/bin/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null || {
        echo "❌ Failed to activate virtual environment"
        echo "Please activate it manually: source venv/bin/activate"
        exit 1
    }
fi

# Install pre-commit if not installed
echo "📦 Installing pre-commit..."
pip install pre-commit detect-secrets bandit black ruff mypy isort pylint pytest pytest-cov

# Install pre-commit hooks
echo "🪝 Installing git hooks..."
pre-commit install
pre-commit install --hook-type commit-msg

# Update hooks to latest versions
echo "🔄 Updating hooks to latest versions..."
pre-commit autoupdate

# Run pre-commit on all files (optional, for initial setup)
echo "🔍 Running initial check on all files..."
pre-commit run --all-files || {
    echo "⚠️  Some files need fixing. Run the following:"
    echo "  black . --line-length=100"
    echo "  isort . --profile black --line-length 100"
    echo "  ruff check --fix ."
}

# Create git hook for additional checks
echo "📝 Creating custom git hook..."
cat > .git/hooks/pre-commit-custom << 'EOF'
#!/bin/bash
# Custom pre-commit hook for BOT_AI_V3

# Run secret detection
python scripts/check_secrets.py --staged --quiet || {
    echo "❌ Secrets detected! Please remove them before committing."
    exit 1
}

# Check for large files
for file in $(git diff --cached --name-only); do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        if [ "$size" -gt 500000 ]; then
            echo "⚠️  Warning: $file is larger than 500KB ($(($size/1024))KB)"
            echo "Consider using Git LFS for large files"
        fi
    fi
done

exit 0
EOF

chmod +x .git/hooks/pre-commit-custom

# Make scripts executable
chmod +x scripts/*.sh
chmod +x scripts/*.py

echo "✅ Pre-commit hooks setup complete!"
echo ""
echo "📋 Available commands:"
echo "  • pre-commit run --all-files    # Run on all files"
echo "  • pre-commit run                # Run on staged files"
echo "  • ./scripts/run_checks.sh        # Run all checks manually"
echo "  • python scripts/pre_commit_check.py  # Comprehensive check"
echo ""
echo "🎯 The hooks will now run automatically before each commit!"
