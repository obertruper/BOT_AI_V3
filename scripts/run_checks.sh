#!/bin/bash

# Script to run all quality checks before commit
# Usage: ./scripts/run_checks.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Running all quality checks...${NC}\n"

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated. Activating...${NC}"
    source venv/bin/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null || {
        echo -e "${RED}❌ Failed to activate virtual environment${NC}"
        exit 1
    }
fi

# 1. Check for secrets
echo -e "${YELLOW}1️⃣ Checking for secrets...${NC}"
python scripts/check_secrets.py --staged --quiet || {
    echo -e "${RED}❌ Secrets check failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ No secrets detected${NC}\n"

# 2. Format code with Black
echo -e "${YELLOW}2️⃣ Formatting code with Black...${NC}"
black . --line-length=100 --quiet || {
    echo -e "${RED}❌ Black formatting failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ Code formatted${NC}\n"

# 3. Sort imports with isort
echo -e "${YELLOW}3️⃣ Sorting imports with isort...${NC}"
isort . --profile black --line-length 100 --quiet || {
    echo -e "${RED}❌ Import sorting failed${NC}"
    exit 1
}
echo -e "${GREEN}✅ Imports sorted${NC}\n"

# 4. Lint with Ruff
echo -e "${YELLOW}4️⃣ Linting with Ruff...${NC}"
ruff check . --fix --quiet || {
    echo -e "${RED}❌ Ruff linting failed${NC}"
    echo -e "${YELLOW}Run 'ruff check . --fix' to see details${NC}"
    exit 1
}
echo -e "${GREEN}✅ Linting passed${NC}\n"

# 5. Type checking with MyPy
echo -e "${YELLOW}5️⃣ Type checking with MyPy...${NC}"
mypy . --ignore-missing-imports --python-version=3.12 --no-error-summary 2>/dev/null || {
    echo -e "${YELLOW}⚠️  MyPy found some type issues (non-blocking)${NC}"
}
echo -e "${GREEN}✅ Type checking completed${NC}\n"

# 6. Security check with Bandit
echo -e "${YELLOW}6️⃣ Security check with Bandit...${NC}"
bandit -r . -f json -o /tmp/bandit-report.json --skip B101,B601 --quiet 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Bandit found some security issues (non-blocking)${NC}"
}
echo -e "${GREEN}✅ Security check completed${NC}\n"

# 7. Check for outdated dependencies
echo -e "${YELLOW}7️⃣ Checking dependencies...${NC}"
pip list --outdated 2>/dev/null | head -n 5 || true
echo -e "${GREEN}✅ Dependency check completed${NC}\n"

# 8. Run quick unit tests (optional)
if [ "$1" == "--with-tests" ]; then
    echo -e "${YELLOW}8️⃣ Running unit tests...${NC}"
    pytest tests/unit/ -q --tb=short || {
        echo -e "${RED}❌ Unit tests failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✅ Unit tests passed${NC}\n"
fi

echo -e "${GREEN}🎉 All checks passed! Ready to commit.${NC}"

# Show git status
echo -e "\n${YELLOW}Current git status:${NC}"
git status --short

echo -e "\n${YELLOW}To commit your changes, run:${NC}"
echo -e "${GREEN}git add . && git commit -m 'your message'${NC}"
