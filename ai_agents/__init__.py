"""
AI Agents для автоматизации разработки и торговых операций
"""

from .agent_manager import (
    AGENT_CONFIGS,
    AgentConfig,
    ClaudeCodeAgent,
    MultiModelOrchestrator,
    autonomous_development,
    collaborative_development,
    develop_strategy,
    generate_tests,
    optimize_performance,
    review_code,
    security_audit,
)
from .agents.architect_agent import (
    ArchitectAgent,
    ArchitectureAnalysis,
    analyze_project_architecture,
    generate_architecture_report,
)
from .agents.autonomous_developer import (
    AutonomousDeveloper,
    DevelopmentResult,
    DevelopmentTask,
    develop_feature_autonomously,
)
from .browser_ai_interface import (
    BrowserAIInterface,
    SmartCrossVerifier,
    TerminalAICommands,
    ask_ai,
    compare_ai,
    cross_verify,
    intelligent_ask,
    research,
    smart_ask,
    upload_and_analyze,
)
from .claude_code_sdk import (
    ClaudeAgentBuilder,
    ClaudeCodeOptions,
    ClaudeCodeSDK,
    PermissionMode,
    ThinkingMode,
    implement_feature,
    quick_review,
)
from .utils import get_mcp_manager

__all__ = [
    # Agent Manager
    "ClaudeCodeAgent",
    "MultiModelOrchestrator",
    "AgentConfig",
    "AGENT_CONFIGS",
    "review_code",
    "generate_tests",
    "develop_strategy",
    "autonomous_development",
    "optimize_performance",
    "security_audit",
    "collaborative_development",
    # Claude Code SDK
    "ClaudeCodeSDK",
    "ClaudeCodeOptions",
    "ClaudeAgentBuilder",
    "ThinkingMode",
    "PermissionMode",
    "quick_review",
    "implement_feature",
    # Browser Interface & Cross Verification
    "BrowserAIInterface",
    "SmartCrossVerifier",
    "TerminalAICommands",
    "ask_ai",
    "smart_ask",
    "cross_verify",
    "compare_ai",
    "intelligent_ask",
    "research",
    "upload_and_analyze",
    # Architect Agent
    "ArchitectAgent",
    "ArchitectureAnalysis",
    "analyze_project_architecture",
    "generate_architecture_report",
    # Autonomous Developer
    "AutonomousDeveloper",
    "DevelopmentTask",
    "DevelopmentResult",
    "develop_feature_autonomously",
    # Utils
    "get_mcp_manager",
]
