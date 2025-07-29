"""
AI Agents для автоматизации разработки и торговых операций
"""
from .agent_manager import (
    ClaudeCodeAgent,
    MultiModelOrchestrator,
    AgentConfig,
    AGENT_CONFIGS,
    review_code,
    generate_tests,
    develop_strategy,
    autonomous_development,
    optimize_performance,
    security_audit,
    collaborative_development
)

from .claude_code_sdk import (
    ClaudeCodeSDK,
    ClaudeCodeOptions,
    ClaudeAgentBuilder,
    ThinkingMode,
    PermissionMode,
    quick_review,
    implement_feature
)

from .browser_ai_interface import (
    BrowserAIInterface,
    SmartCrossVerifier,
    TerminalAICommands,
    ask_ai,
    smart_ask,
    cross_verify,
    compare_ai,
    intelligent_ask,
    research,
    upload_and_analyze
)

from .agents.architect_agent import (
    ArchitectAgent,
    ArchitectureAnalysis,
    analyze_project_architecture,
    generate_architecture_report
)

from .agents.autonomous_developer import (
    AutonomousDeveloper,
    DevelopmentTask,
    DevelopmentResult,
    develop_feature_autonomously
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
    "get_mcp_manager"
]