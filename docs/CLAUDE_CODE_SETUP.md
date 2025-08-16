# Claude Code GitHub Action Setup Guide

## Overview

This repository is configured with Claude Code GitHub Action for automated code review, assistance, and analysis. Claude will automatically review pull requests and respond to mentions in comments.

## Features

### 1. Automatic PR Review

- Claude automatically reviews all pull requests
- Checks for security issues, code quality, and project-specific requirements
- Posts detailed feedback as PR comments

### 2. Interactive Assistance

- Mention `@claude` or `/claude` in any comment to get help
- Claude can answer questions, explain code, and suggest improvements

### 3. Command Triggers

Available commands in PR/Issue comments:

- `/claude analyze` - Comprehensive code analysis
- `/claude fix` - Attempt to fix identified issues
- `/claude explain` - Explain code functionality
- `/claude optimize` - Suggest optimizations
- `/claude security` - Security audit

## Setup Instructions

### 1. Add Required Secrets

Go to your repository settings → Secrets and variables → Actions, and add:

```bash
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

To get an Anthropic API key:

1. Go to <https://console.anthropic.com/>
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and add it to GitHub secrets

### 2. Verify Workflow Files

The following workflow files should be present:

- `.github/workflows/claude-code.yml` - Main Claude Code workflow
- `.claude-code.yml` - Project-specific configuration

### 3. Test the Setup

1. Create a test PR with some code changes
2. Wait for Claude to automatically review it
3. Try commenting `@claude explain this code` on a file

## Project-Specific Configuration

### Critical Settings for BOT_AI_V3

Claude is configured with these project-specific rules:

1. **PostgreSQL Port**: Always uses port 5555 (NOT 5432)
2. **Async/Await**: All I/O operations must be async
3. **API Keys**: Only stored in `.env` file, never in code
4. **Type Hints**: Required for all Python functions
5. **Imports**: Use absolute imports from project root

### Review Focus Areas

Claude prioritizes reviewing:

- Security vulnerabilities
- Async pattern violations
- Database connection issues
- Type safety problems
- Error handling gaps

## Usage Examples

### Getting Code Review

Simply create a pull request. Claude will automatically:

1. Review all changed files
2. Check against project standards
3. Post detailed feedback
4. Suggest improvements

### Asking Questions

In any PR or issue comment:

```
@claude How does the ML signal processing work in this project?
```

```
/claude explain the trading engine architecture
```

### Requesting Analysis

For comprehensive analysis:

```
/claude analyze
```

This will trigger a full repository analysis covering:

- Architecture and design patterns
- Security vulnerabilities
- Performance bottlenecks
- Code quality metrics
- Test coverage gaps

## Troubleshooting

### Claude Not Responding

1. Check if `ANTHROPIC_API_KEY` secret is set
2. Verify workflow files are in `.github/workflows/`
3. Check Actions tab for workflow run logs
4. Ensure you're using correct trigger phrases

### Rate Limiting

Claude has built-in rate limiting. If you hit limits:

- Wait a few minutes before retrying
- Use more specific questions
- Batch multiple questions in one comment

### Workflow Failures

Check the Actions tab for detailed logs:

1. Go to repository → Actions
2. Click on the failed workflow run
3. Review logs for error messages

## Best Practices

### 1. Clear Questions

Be specific when asking Claude:

- ❌ "Fix this"
- ✅ "Fix the async/await pattern in the submit_order function"

### 2. Provide Context

Include relevant information:

- ❌ "Why doesn't this work?"
- ✅ "This PostgreSQL query fails with port 5555, error: connection refused"

### 3. Use Commands Appropriately

- Use `/claude analyze` for comprehensive reviews
- Use `@claude` for specific questions
- Use `/claude fix` only for simple, clear issues

## Integration with CI/CD

Claude Code is integrated with our CI/CD pipeline:

1. **Pre-commit**: Local code quality checks
2. **Claude Review**: AI-powered code review on PR
3. **GitHub Actions**: Automated testing and validation
4. **Deployment**: Only after all checks pass

## Security Considerations

### Protected Information

Claude will never expose:

- API keys or secrets
- Database credentials
- Private keys
- Sensitive configuration

### Safe Practices

- Claude reviews are public - avoid sharing sensitive data
- Use environment variables for all secrets
- Review Claude's suggestions before implementing

## Support

For issues or questions:

1. Check this documentation
2. Review [Claude Code Action docs](https://github.com/anthropics/claude-code-action)
3. Open an issue in this repository
4. Contact the maintainers

## Updates

This configuration uses Claude Code Action v1. Check for updates:

```bash
# Check current version
grep "anthropics/claude-code-action" .github/workflows/claude-code.yml

# Update to latest
# Edit .github/workflows/claude-code.yml and change version tag
```

---

**Last Updated**: January 2025
**Claude Model**: claude-3-5-sonnet-20241022
**Action Version**: v1
