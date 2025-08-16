#!/usr/bin/env python3
"""
Comprehensive pre-commit check script.
Runs all necessary quality checks before allowing a commit.
"""

import os
import subprocess
import sys
import time


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    MAGENTA = "\033[0;35m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # No Color


def run_command(cmd: list[str], description: str, allow_failure: bool = False) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    print(f"{Colors.YELLOW}🔧 {description}...{Colors.NC}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=not allow_failure)

        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ {description} passed{Colors.NC}")
            return True, result.stdout
        else:
            if allow_failure:
                print(f"{Colors.YELLOW}⚠️  {description} has warnings (non-blocking){Colors.NC}")
                return True, result.stdout
            else:
                print(f"{Colors.RED}❌ {description} failed{Colors.NC}")
                if result.stderr:
                    print(f"{Colors.RED}{result.stderr}{Colors.NC}")
                return False, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ {description} failed{Colors.NC}")
        if e.stderr:
            print(f"{Colors.RED}{e.stderr}{Colors.NC}")
        return False, str(e)
    except FileNotFoundError:
        print(f"{Colors.YELLOW}⚠️  {description} tool not found (skipping){Colors.NC}")
        return True, "Tool not found"


def check_virtual_env() -> bool:
    """Check if virtual environment is activated."""
    if not os.environ.get("VIRTUAL_ENV"):
        print(f"{Colors.RED}❌ Virtual environment not activated!{Colors.NC}")
        print(f"{Colors.YELLOW}Please run: source venv/bin/activate{Colors.NC}")
        return False
    return True


def get_changed_files() -> list[str]:
    """Get list of changed Python files."""
    try:
        # Get staged files
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )

        files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # Filter Python files
        python_files = [f for f in files if f.endswith(".py") and os.path.exists(f)]

        return python_files
    except subprocess.CalledProcessError:
        return []


def check_file_size() -> bool:
    """Check for large files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
        )

        files = result.stdout.strip().split("\n") if result.stdout.strip() else []
        large_files = []

        for file in files:
            if os.path.exists(file):
                size = os.path.getsize(file)
                if size > 500000:  # 500KB
                    large_files.append((file, size))

        if large_files:
            print(f"{Colors.YELLOW}⚠️  Large files detected:{Colors.NC}")
            for file, size in large_files:
                print(f"  {file}: {size / 1024:.1f}KB")
            return False

        return True
    except Exception:
        return True


def run_all_checks() -> bool:
    """Run all pre-commit checks."""
    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.NC}")
    print(f"{Colors.CYAN}🚀 Running Pre-Commit Checks{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 60}{Colors.NC}\n")

    start_time = time.time()
    all_passed = True

    # Check virtual environment
    if not check_virtual_env():
        return False

    # Get changed files
    changed_files = get_changed_files()
    if changed_files:
        print(f"{Colors.BLUE}📝 Checking {len(changed_files)} Python files{Colors.NC}\n")

    # 1. Check for secrets
    success, _ = run_command(
        ["python", "scripts/check_secrets.py", "--staged", "--quiet"],
        "Secret detection",
        allow_failure=False,
    )
    if not success:
        all_passed = False
        print(f"{Colors.YELLOW}Fix: Remove secrets and use environment variables{Colors.NC}\n")

    # 2. Check file sizes
    if not check_file_size():
        print(f"{Colors.YELLOW}⚠️  Consider using Git LFS for large files{Colors.NC}\n")

    # 3. Format with Black
    if changed_files:
        success, _ = run_command(
            ["black", "--check", "--line-length=100"] + changed_files,
            "Black formatting check",
            allow_failure=False,
        )
        if not success:
            print(f"{Colors.YELLOW}Fix: Run 'black . --line-length=100'{Colors.NC}\n")
            all_passed = False

    # 4. Sort imports with isort
    if changed_files:
        success, _ = run_command(
            ["isort", "--check-only", "--profile", "black", "--line-length", "100"] + changed_files,
            "Import sorting check",
            allow_failure=False,
        )
        if not success:
            print(
                f"{Colors.YELLOW}Fix: Run 'isort . --profile black --line-length 100'{Colors.NC}\n"
            )
            all_passed = False

    # 5. Lint with Ruff
    if changed_files:
        success, _ = run_command(
            ["ruff", "check"] + changed_files, "Ruff linting", allow_failure=False
        )
        if not success:
            print(f"{Colors.YELLOW}Fix: Run 'ruff check --fix .'{Colors.NC}\n")
            all_passed = False

    # 6. Type checking with MyPy (non-blocking)
    if changed_files:
        run_command(
            ["mypy", "--ignore-missing-imports", "--python-version=3.12"] + changed_files,
            "Type checking",
            allow_failure=True,
        )

    # 7. Security check with Bandit (non-blocking)
    if changed_files:
        run_command(
            ["bandit", "-r", "--skip", "B101,B601"] + changed_files,
            "Security scan",
            allow_failure=True,
        )

    # 8. Check for debugging statements
    for file in changed_files:
        with open(file) as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                if "import pdb" in line or "pdb.set_trace()" in line:
                    print(f"{Colors.RED}❌ Debugging statement found in {file}:{i}{Colors.NC}")
                    all_passed = False
                if "print(" in line and "# noqa" not in line and "test" not in file.lower():
                    print(f"{Colors.YELLOW}⚠️  Print statement in {file}:{i}{Colors.NC}")

    # Summary
    elapsed_time = time.time() - start_time
    print(f"\n{Colors.CYAN}{'=' * 60}{Colors.NC}")

    if all_passed:
        print(f"{Colors.GREEN}✅ All checks passed! ({elapsed_time:.1f}s){Colors.NC}")
        print(f"{Colors.GREEN}Ready to commit!{Colors.NC}")
    else:
        print(f"{Colors.RED}❌ Some checks failed! ({elapsed_time:.1f}s){Colors.NC}")
        print(f"{Colors.YELLOW}Please fix the issues before committing.{Colors.NC}")

    print(f"{Colors.CYAN}{'=' * 60}{Colors.NC}\n")

    return all_passed


def main():
    """Main function."""
    # Check if we're in the right directory
    if not os.path.exists("unified_launcher.py"):
        print(f"{Colors.RED}❌ Not in BOT_AI_V3 root directory!{Colors.NC}")
        sys.exit(1)

    # Run all checks
    if run_all_checks():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
