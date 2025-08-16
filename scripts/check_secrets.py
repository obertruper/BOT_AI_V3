#!/usr/bin/env python3
"""
Script to check for exposed secrets and API keys in code before commit.
"""

import os
import re
import sys
from pathlib import Path

# Patterns to detect secrets
SECRET_PATTERNS = [
    # Exchange API keys and secrets
    (
        r'(?i)(bybit|binance|okx|gate|kucoin|htx|bingx)[-_]?(api)?[-_]?(key|secret)[^:=]*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{20,})',
        "Exchange API credentials",
    ),
    # PostgreSQL passwords
    (
        r'(?i)(pg|postgres|postgresql)[-_]?password[^:=]*[:=]\s*[\'"]?([a-zA-Z0-9\-_!@#$%^&*()]{8,})',
        "PostgreSQL password",
    ),
    # JWT tokens
    (r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*", "JWT token"),
    # Private keys
    (r"-----BEGIN (RSA|EC|OPENSSH|DSA|SSH2|PGP) PRIVATE KEY-----", "Private key"),
    # AWS keys
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (
        r'(?i)aws[-_]?secret[-_]?access[-_]?key[^:=]*[:=]\s*[\'"]?([a-zA-Z0-9/+=]{40})',
        "AWS Secret Key",
    ),
    # Generic API keys
    (r'(?i)api[-_]?key[^:=]*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{32,})', "API Key"),
    (r'(?i)api[-_]?secret[^:=]*[:=]\s*[\'"]?([a-zA-Z0-9\-_]{32,})', "API Secret"),
    # Telegram bot tokens
    (r"[0-9]{8,10}:[a-zA-Z0-9_-]{35}", "Telegram Bot Token"),
    # Database URLs with credentials
    (
        r"(?i)(postgres|postgresql|mysql|mongodb|redis)://[^:]+:[^@]+@[^/]+/[^\s]+",
        "Database URL with credentials",
    ),
]

# Files to skip
SKIP_FILES = {
    ".env.example",
    ".env.test",
    ".secrets.baseline",
    "requirements.txt",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
}

# Directories to skip
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "build",
    "dist",
    "data",
    "logs",
}

# Extensions to check
CHECK_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".sh",
    ".bash",
    ".zsh",
    ".env",
    ".ini",
    ".cfg",
    ".conf",
    ".sql",
    ".md",
    ".txt",
}


def is_test_file(filepath: Path) -> bool:
    """Check if file is a test file."""
    return "test" in filepath.name.lower() or filepath.parts[-2:] == ("tests",)


def should_check_file(filepath: Path) -> bool:
    """Check if file should be scanned for secrets."""
    # Skip if in skip list
    if filepath.name in SKIP_FILES:
        return False

    # Skip if in skip directory
    for part in filepath.parts:
        if part in SKIP_DIRS:
            return False

    # Skip if no extension or not in check list
    if filepath.suffix and filepath.suffix not in CHECK_EXTENSIONS:
        return False

    return True


def check_line_for_secrets(line: str, line_num: int, filepath: Path) -> list[tuple[str, int, str]]:
    """Check a single line for secrets."""
    findings = []

    # Skip if line has allowlist comment
    if "pragma: allowlist" in line or "# noqa: secret" in line:
        return findings

    # Skip if it's a test file and contains test/dummy/fake
    if is_test_file(filepath):
        lower_line = line.lower()
        if any(word in lower_line for word in ["test", "dummy", "fake", "example", "mock"]):
            return findings

    # Check against all patterns
    for pattern, description in SECRET_PATTERNS:
        if re.search(pattern, line):
            findings.append((description, line_num, line.strip()))

    return findings


def scan_file(filepath: Path) -> list[tuple[str, int, str]]:
    """Scan a file for secrets."""
    findings = []

    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                findings.extend(check_line_for_secrets(line, line_num, filepath))
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)

    return findings


def get_staged_files() -> set[Path]:
    """Get list of staged files in git."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, check=True
        )
        return {Path(f) for f in result.stdout.strip().split("\n") if f}
    except subprocess.CalledProcessError:
        # If not in a git repo, check all files
        return set()


def scan_directory(directory: Path, staged_only: bool = False) -> dict:
    """Scan directory for secrets."""
    all_findings = {}

    if staged_only:
        files_to_check = get_staged_files()
        if not files_to_check:
            print("No staged files to check")
            return all_findings
    else:
        files_to_check = set()
        for root, dirs, files in os.walk(directory):
            # Remove skip directories from dirs to prevent walking into them
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for file in files:
                filepath = Path(root) / file
                if should_check_file(filepath):
                    files_to_check.add(filepath)

    for filepath in files_to_check:
        if filepath.exists() and should_check_file(filepath):
            findings = scan_file(filepath)
            if findings:
                all_findings[str(filepath)] = findings

    return all_findings


def print_findings(findings: dict) -> None:
    """Print findings in a formatted way."""
    if not findings:
        print("✅ No secrets detected!")
        return

    print("⚠️  POTENTIAL SECRETS DETECTED:")
    print("-" * 80)

    for filepath, file_findings in findings.items():
        print(f"\n📄 {filepath}")
        for description, line_num, line_content in file_findings:
            # Truncate long lines
            if len(line_content) > 100:
                line_content = line_content[:97] + "..."
            print(f"  Line {line_num}: {description}")
            print(f"    {line_content}")

    print("\n" + "-" * 80)
    print(
        f"Total: {sum(len(f) for f in findings.values())} potential secrets in {len(findings)} files"
    )


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Check for exposed secrets in code")
    parser.add_argument(
        "path", nargs="?", default=".", help="Path to scan (default: current directory)"
    )
    parser.add_argument(
        "--staged", action="store_true", help="Only check staged files (for pre-commit)"
    )
    parser.add_argument("--quiet", action="store_true", help="Only show summary")

    args = parser.parse_args()

    scan_path = Path(args.path).resolve()

    if not scan_path.exists():
        print(f"Error: Path {scan_path} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Scanning {'staged files' if args.staged else scan_path} for secrets...")

    findings = scan_directory(scan_path, staged_only=args.staged)

    if not args.quiet:
        print_findings(findings)

    if findings:
        print("\n❌ Pre-commit check failed: Secrets detected!")
        print("📝 To fix:")
        print("  1. Remove the secrets from your code")
        print("  2. Use environment variables or .env files instead")
        print("  3. Add '# pragma: allowlist secret' comment if it's a false positive")
        sys.exit(1)
    else:
        if not args.quiet:
            print("✅ No secrets detected!")
        sys.exit(0)


if __name__ == "__main__":
    main()
