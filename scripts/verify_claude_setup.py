#!/usr/bin/env python3
"""
Verify Claude Code GitHub Action setup for BOT_AI_V3 project.

This script checks that all necessary configurations are in place
for Claude Code to work properly with the repository.
"""

import json
import sys
from pathlib import Path

import yaml


class ClaudeSetupVerifier:
    """Verifies Claude Code setup and configuration."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.success: list[str] = []

    def check_workflow_files(self) -> bool:
        """Check if Claude workflow files exist."""
        workflow_dir = self.project_root / ".github" / "workflows"
        required_files = ["claude-code.yml"]

        for file in required_files:
            file_path = workflow_dir / file
            if file_path.exists():
                self.success.append(f"✅ Workflow file exists: {file}")

                # Validate workflow content
                try:
                    with open(file_path) as f:
                        workflow = yaml.safe_load(f)

                    # Check for required configuration
                    if "jobs" in workflow:
                        if "claude-assistant" in workflow["jobs"]:
                            self.success.append("  - claude-assistant job configured")
                        if "claude-auto-review" in workflow["jobs"]:
                            self.success.append("  - claude-auto-review job configured")
                        if "claude-analyze" in workflow["jobs"]:
                            self.success.append("  - claude-analyze job configured")

                    # Check for API key reference
                    workflow_str = file_path.read_text()
                    if "ANTHROPIC_API_KEY" in workflow_str:
                        self.success.append("  - ANTHROPIC_API_KEY secret referenced")
                    else:
                        self.errors.append(f"❌ ANTHROPIC_API_KEY not found in {file}")

                except Exception as e:
                    self.errors.append(f"❌ Error parsing {file}: {e}")
            else:
                self.errors.append(f"❌ Missing workflow file: {file}")

        return len(self.errors) == 0

    def check_configuration_file(self) -> bool:
        """Check Claude Code configuration file."""
        config_file = self.project_root / ".claude-code.yml"

        if config_file.exists():
            self.success.append("✅ Configuration file exists: .claude-code.yml")

            try:
                with open(config_file) as f:
                    config = yaml.safe_load(f)

                # Check critical settings
                if config.get("database", {}).get("port") == 5555:
                    self.success.append("  - PostgreSQL port correctly set to 5555")
                else:
                    self.errors.append("❌ PostgreSQL port not set to 5555")

                if config.get("project", {}).get("python_version") == "3.12":
                    self.success.append("  - Python version correctly set to 3.12")

                if "instructions" in config:
                    self.success.append("  - Custom instructions configured")

                if "security" in config:
                    self.success.append("  - Security rules configured")

            except Exception as e:
                self.errors.append(f"❌ Error parsing .claude-code.yml: {e}")
        else:
            self.warnings.append("⚠️ Missing .claude-code.yml configuration file")

        return True

    def check_github_settings(self) -> bool:
        """Check GitHub repository settings."""
        # Check for .env.example
        env_example = self.project_root / ".env.example"
        if env_example.exists():
            self.success.append("✅ .env.example exists for reference")

            # Check if it has ANTHROPIC_API_KEY placeholder
            if "ANTHROPIC_API_KEY" in env_example.read_text():
                self.success.append("  - ANTHROPIC_API_KEY placeholder present")
        else:
            self.warnings.append("⚠️ No .env.example file for API key reference")

        # Check .gitignore
        gitignore = self.project_root / ".gitignore"
        if gitignore.exists():
            gitignore_content = gitignore.read_text()
            if ".env" in gitignore_content:
                self.success.append("✅ .env is in .gitignore")
            else:
                self.errors.append("❌ .env not in .gitignore - secrets may be exposed!")

        return True

    def check_documentation(self) -> bool:
        """Check if Claude Code documentation exists."""
        docs = ["docs/CLAUDE_CODE_SETUP.md", "docs/CODE_QUALITY.md", "CLAUDE.md"]

        for doc in docs:
            doc_path = self.project_root / doc
            if doc_path.exists():
                self.success.append(f"✅ Documentation exists: {doc}")
            else:
                self.warnings.append(f"⚠️ Missing documentation: {doc}")

        return True

    def check_mcp_compatibility(self) -> bool:
        """Check MCP (Model Context Protocol) compatibility."""
        mcp_files = [".mcp.json", "mcp.json", ".claude-mcp-config.json"]

        mcp_found = False
        for mcp_file in mcp_files:
            mcp_path = self.project_root / mcp_file
            if mcp_path.exists():
                self.success.append(f"✅ MCP configuration found: {mcp_file}")
                mcp_found = True

                # Validate MCP configuration
                try:
                    with open(mcp_path) as f:
                        mcp_config = json.load(f)

                    if "mcpServers" in mcp_config:
                        servers = list(mcp_config["mcpServers"].keys())
                        self.success.append(f"  - MCP servers: {', '.join(servers)}")

                except Exception as e:
                    self.warnings.append(f"⚠️ Error parsing {mcp_file}: {e}")

        if not mcp_found:
            self.warnings.append("⚠️ No MCP configuration file found")

        return True

    def check_project_specific_requirements(self) -> bool:
        """Check BOT_AI_V3 specific requirements."""
        requirements = [
            ("PostgreSQL port 5555", self._check_postgres_port),
            ("Async/await patterns", self._check_async_patterns),
            ("Type hints usage", self._check_type_hints),
            ("Environment variables", self._check_env_usage),
        ]

        for req_name, check_func in requirements:
            try:
                if check_func():
                    self.success.append(f"✅ {req_name} check passed")
                else:
                    self.warnings.append(f"⚠️ {req_name} needs review")
            except Exception as e:
                self.warnings.append(f"⚠️ Could not check {req_name}: {e}")

        return True

    def _check_postgres_port(self) -> bool:
        """Check if PostgreSQL port 5555 is used."""
        files_to_check = [
            "config/database.yaml",
            "config/system.yaml",
            ".env.example",
            "docker-compose.yml",
        ]

        for file in files_to_check:
            file_path = self.project_root / file
            if file_path.exists():
                content = file_path.read_text()
                if "5432" in content and "5555" not in content:
                    return False

        return True

    def _check_async_patterns(self) -> bool:
        """Check for async/await usage in Python files."""
        # This is a simple check - just verify async functions exist
        py_files = list((self.project_root / "trading").glob("**/*.py"))[:5]

        async_found = False
        for py_file in py_files:
            content = py_file.read_text()
            if "async def" in content and "await" in content:
                async_found = True
                break

        return async_found

    def _check_type_hints(self) -> bool:
        """Check for type hints in Python files."""
        py_files = list((self.project_root / "core").glob("**/*.py"))[:5]

        hints_found = False
        for py_file in py_files:
            content = py_file.read_text()
            if "-> " in content or ": " in content:
                hints_found = True
                break

        return hints_found

    def _check_env_usage(self) -> bool:
        """Check that environment variables are used for secrets."""
        suspicious_patterns = ['api_key = "', 'api_secret = "', 'API_KEY = "', 'API_SECRET = "']

        py_files = list(self.project_root.glob("**/*.py"))[:20]

        for py_file in py_files:
            if "venv" in str(py_file) or "__pycache__" in str(py_file):
                continue

            content = py_file.read_text()
            for pattern in suspicious_patterns:
                if pattern in content and "os.getenv" not in content:
                    return False

        return True

    def run_verification(self) -> tuple[bool, str]:
        """Run all verification checks."""
        print("🔍 Verifying Claude Code Setup for BOT_AI_V3\n")
        print("=" * 60)

        # Run all checks
        checks = [
            ("Workflow Files", self.check_workflow_files),
            ("Configuration File", self.check_configuration_file),
            ("GitHub Settings", self.check_github_settings),
            ("Documentation", self.check_documentation),
            ("MCP Compatibility", self.check_mcp_compatibility),
            ("Project Requirements", self.check_project_specific_requirements),
        ]

        for check_name, check_func in checks:
            print(f"\n📋 Checking {check_name}...")
            check_func()

        # Generate report
        print("\n" + "=" * 60)
        print("📊 VERIFICATION REPORT\n")

        if self.success:
            print("✅ SUCCESSFUL CHECKS:")
            for msg in self.success:
                print(f"  {msg}")

        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for msg in self.warnings:
                print(f"  {msg}")

        if self.errors:
            print("\n❌ ERRORS (must fix):")
            for msg in self.errors:
                print(f"  {msg}")

        # Overall status
        print("\n" + "=" * 60)
        if not self.errors:
            print("✅ Claude Code setup is READY!")
            print("\n📝 Next steps:")
            print("1. Add ANTHROPIC_API_KEY to GitHub secrets")
            print("2. Create a test PR to verify auto-review")
            print("3. Try '@claude' mention in comments")
            return True, "Setup verified successfully"
        else:
            print("❌ Claude Code setup has ERRORS that need fixing")
            print("\nRefer to docs/CLAUDE_CODE_SETUP.md for setup instructions")
            return False, f"Found {len(self.errors)} errors"


def main():
    """Main entry point."""
    verifier = ClaudeSetupVerifier()
    success, message = verifier.run_verification()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
