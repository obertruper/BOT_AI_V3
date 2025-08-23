#!/bin/bash
# Setup script for OpenAI Codex CLI integration with BOT_AI_V3

echo "🚀 Setting up OpenAI Codex CLI for BOT_AI_V3..."
echo ""

# Check if Codex is installed
if ! command -v codex &> /dev/null; then
    echo "❌ Codex CLI not found. Installing..."
    npm install -g @openai/codex
else
    echo "✅ Codex CLI is installed: $(codex --version)"
fi

# Create .codex directory if it doesn't exist
mkdir -p ~/.codex

# Create config.toml for Codex
cat > ~/.codex/config.toml << 'EOF'
# OpenAI Codex CLI Configuration for BOT_AI_V3

[project]
name = "BOT_AI_V3"
root = "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3"

[autonomy]
# Controls the level of autonomy for Codex
# Options: "read_write", "read_only", "custom"
mode = "read_write"

[sandbox]
# Allow Codex to run commands in sandbox
enabled = true

[model]
# Default model to use
default = "gpt-5"

[context]
# Files to include in context
include = [
    "*.py",
    "*.yaml",
    "*.json",
    "requirements.txt",
    "CLAUDE.md",
    "README.md"
]

# Files to exclude
exclude = [
    "__pycache__",
    "*.pyc",
    ".git",
    "venv/",
    ".env"
]

[memory]
# Enable memory for project-specific context
enabled = true
path = "~/.codex/memory/bot_ai_v3.json"
EOF

echo "✅ Created Codex configuration at ~/.codex/config.toml"
echo ""

# Create project-specific Codex memory
mkdir -p ~/.codex/memory

cat > ~/.codex/memory/bot_ai_v3.json << 'EOF'
{
  "project": "BOT_AI_V3",
  "description": "AI Trading Bot with ML predictions and Dynamic SL/TP",
  "key_components": {
    "trading_engine": "trading/engine.py - Main trading engine with signal processing",
    "ml_manager": "ml/ml_manager.py - ML model management with UnifiedPatchTST",
    "orchestrator": "core/system/orchestrator.py - System orchestration",
    "dynamic_sltp": "trading/orders/dynamic_sltp_calculator.py - Dynamic Stop Loss/Take Profit",
    "risk_manager": "risk_management/manager.py - Risk management with 5x leverage"
  },
  "important_notes": [
    "PostgreSQL runs on port 5555, not 5432",
    "Always activate venv before running: source venv/bin/activate",
    "Leverage is 5x, not 10x",
    "Use async/await for all I/O operations",
    "ML model uses torch.compile for 7.7x speedup"
  ],
  "common_commands": {
    "start_system": "./quick_start.sh",
    "run_tests": "pytest tests/ -v",
    "format_code": "black . && ruff check --fix .",
    "check_types": "mypy . --ignore-missing-imports",
    "start_trading": "python3 unified_launcher.py"
  }
}
EOF

echo "✅ Created project memory at ~/.codex/memory/bot_ai_v3.json"
echo ""

# Check authentication status
echo "🔐 Checking authentication status..."
if [ -f ~/.codex/auth.json ]; then
    echo "✅ Authentication file found"
else
    echo "⚠️  No authentication found. Run one of the following:"
    echo "   1. codex login          (for ChatGPT Plus/Pro/Team users)"
    echo "   2. export OPENAI_API_KEY=your-key-here  (for API key users)"
fi

echo ""
echo "📝 Usage Instructions:"
echo "===================="
echo "1. Start Codex CLI: codex"
echo "2. Use with a prompt: codex 'fix the trading engine tests'"
echo "3. Read-only mode: codex --read-only"
echo "4. With specific file: codex --file trading/engine.py 'optimize this code'"
echo ""
echo "🎯 Integration with BOT_AI_V3:"
echo "==============================="
echo "Codex now has context about your trading bot project including:"
echo "- Key components and their locations"
echo "- Important configuration notes"
echo "- Common commands and workflows"
echo ""
echo "✅ Setup complete! You can now use 'codex' command in your project."