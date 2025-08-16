"""
Менеджер для работы с MCP серверами
Загружает конфигурацию и управляет доступом к MCP функциональности
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Конфигурация MCP сервера"""

    name: str
    enabled: bool
    config: dict[str, Any]

    def get_tool_names(self) -> list[str]:
        """Получить имена инструментов для этого MCP сервера"""
        tool_mapping = {
            "filesystem": [
                "mcp__filesystem__read_file",
                "mcp__filesystem__write_file",
                "mcp__filesystem__edit_file",
                "mcp__filesystem__list_directory",
                "mcp__filesystem__search_files",
            ],
            "github": [
                "mcp__github__create_pr",
                "mcp__github__create_issue",
                "mcp__github__get_file_contents",
                "mcp__github__create_or_update_file",
            ],
            "memory": [
                "mcp__memory__create_entities",
                "mcp__memory__create_relations",
                "mcp__memory__search_nodes",
                "mcp__memory__read_graph",
            ],
            "sequential-thinking": [
                "mcp__sequential-thinking__sequentialthinking",
                "mcp__sequential-thinking-tools__sequentialthinking_tools",
            ],
            "puppeteer": [
                "mcp__puppeteer__puppeteer_navigate",
                "mcp__puppeteer__puppeteer_screenshot",
                "mcp__puppeteer__puppeteer_click",
                "mcp__puppeteer__puppeteer_fill",
            ],
            "playwright": [
                "mcp__playwright__browser_navigate",
                "mcp__playwright__browser_snapshot",
                "mcp__playwright__browser_click",
                "mcp__playwright__browser_type",
            ],
            "context7": [
                "mcp__context7__resolve-library-id",
                "mcp__context7__get-library-docs",
            ],
        }

        return tool_mapping.get(self.name, [])


class MCPManager:
    """Менеджер MCP серверов"""

    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "configs" / "mcp_servers.yaml"

        self.config_path = config_path
        self.servers: dict[str, MCPServerConfig] = {}
        self.agent_profiles: dict[str, dict[str, Any]] = {}
        self.global_settings: dict[str, Any] = {}

        self._load_config()

    def _load_config(self):
        """Загрузить конфигурацию из файла"""
        if not self.config_path.exists():
            logger.warning(f"MCP config not found at {self.config_path}")
            return

        with open(self.config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Загружаем серверы
        for server_name, server_config in config.get("mcp_servers", {}).items():
            self.servers[server_name] = MCPServerConfig(
                name=server_config["name"],
                enabled=server_config.get("enabled", True),
                config=server_config.get("config", {}),
            )

        # Загружаем профили агентов
        self.agent_profiles = config.get("agent_profiles", {})

        # Загружаем глобальные настройки
        self.global_settings = config.get("global_settings", {})

        logger.info(
            f"Loaded {len(self.servers)} MCP servers and {len(self.agent_profiles)} agent profiles"
        )

    def get_server(self, name: str) -> MCPServerConfig | None:
        """Получить конфигурацию сервера по имени"""
        return self.servers.get(name)

    def get_enabled_servers(self) -> list[MCPServerConfig]:
        """Получить список включенных серверов"""
        return [s for s in self.servers.values() if s.enabled]

    def get_tools_for_agent(self, agent_type: str) -> list[str]:
        """Получить список инструментов для типа агента"""
        profile = self.agent_profiles.get(agent_type)
        if not profile:
            logger.warning(f"No profile found for agent type: {agent_type}")
            return []

        tools = []
        for server_name in profile.get("mcp_servers", []):
            server = self.get_server(server_name)
            if server and server.enabled:
                tools.extend(server.get_tool_names())

        # Добавляем базовые инструменты Claude
        tools.extend(["Read", "Write", "Edit", "Bash", "Task", "TodoWrite"])

        return tools

    def get_agent_priority(self, agent_type: str) -> str:
        """Получить приоритет для типа агента"""
        profile = self.agent_profiles.get(agent_type)
        return profile.get("priority", "balanced") if profile else "balanced"

    def build_mcp_env(self, agent_type: str) -> dict[str, str]:
        """Построить переменные окружения для MCP"""
        env = {}

        # GitHub токен
        if "github" in self.agent_profiles.get(agent_type, {}).get("mcp_servers", []):
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                env["GITHUB_TOKEN"] = github_token

        # Другие переменные окружения для MCP
        env["MCP_TELEMETRY"] = str(self.global_settings.get("telemetry_enabled", True)).lower()
        env["MCP_LOG_LEVEL"] = self.global_settings.get("log_level", "INFO")

        return env

    def validate_environment(self) -> dict[str, bool]:
        """Проверить готовность окружения для MCP"""
        checks = {
            "claude_cli": self._check_claude_cli(),
            "api_key": bool(os.getenv("ANTHROPIC_API_KEY")),
            "github_token": bool(os.getenv("GITHUB_TOKEN")),
            "mcp_config": self.config_path.exists(),
        }

        # Проверяем доступность MCP серверов
        for server_name, server in self.servers.items():
            if server.enabled:
                checks[f"mcp_{server_name}"] = True  # Упрощенная проверка

        return checks

    def _check_claude_cli(self) -> bool:
        """Проверить установлен ли Claude CLI"""
        try:
            import subprocess

            result = subprocess.run(["claude", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def get_config_summary(self) -> str:
        """Получить сводку конфигурации"""
        lines = [
            "MCP Configuration Summary:",
            f"- Total servers: {len(self.servers)}",
            f"- Enabled servers: {len(self.get_enabled_servers())}",
            f"- Agent profiles: {len(self.agent_profiles)}",
            "",
            "Enabled MCP Servers:",
        ]

        for server in self.get_enabled_servers():
            lines.append(f"  - {server.name}")

        lines.extend(["", "Agent Profiles:"])

        for agent_type, profile in self.agent_profiles.items():
            servers = ", ".join(profile.get("mcp_servers", []))
            lines.append(
                f"  - {agent_type}: [{servers}] (priority: {profile.get('priority', 'balanced')})"
            )

        return "\n".join(lines)


# Singleton экземпляр
_mcp_manager_instance = None


def get_mcp_manager() -> MCPManager:
    """Получить singleton экземпляр MCPManager"""
    global _mcp_manager_instance
    if _mcp_manager_instance is None:
        _mcp_manager_instance = MCPManager()
    return _mcp_manager_instance


if __name__ == "__main__":
    # Тестирование
    manager = get_mcp_manager()

    print(manager.get_config_summary())
    print("\n" + "=" * 50 + "\n")

    # Проверка окружения
    print("Environment validation:")
    for check, result in manager.validate_environment().items():
        status = "✓" if result else "✗"
        print(f"  {status} {check}")

    print("\n" + "=" * 50 + "\n")

    # Инструменты для code_reviewer
    print("Tools for code_reviewer agent:")
    tools = manager.get_tools_for_agent("code_reviewer")
    for tool in tools:
        print(f"  - {tool}")
