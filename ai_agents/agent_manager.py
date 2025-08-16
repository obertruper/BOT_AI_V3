"""
AI Agent Manager для автоматизации разработки и торговых операций
Использует Claude Code SDK и MCP серверы для расширенной функциональности
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .claude_code_sdk import ClaudeCodeOptions, ClaudeCodeSDK, PermissionMode, ThinkingMode
from .utils.mcp_manager import get_mcp_manager

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Конфигурация для AI агента"""

    name: str
    role: str
    system_prompt: str
    allowed_tools: list[str]
    max_turns: int = 5
    model: str = "sonnet"  # Можно использовать "opus", "sonnet" или "haiku"
    thinking_mode: ThinkingMode = ThinkingMode.NORMAL
    permission_mode: PermissionMode = PermissionMode.DEFAULT


class ClaudeCodeAgent:
    """Агент для работы с Claude Code SDK"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.working_dir = Path.cwd()
        self.sdk = ClaudeCodeSDK()
        self.mcp_manager = get_mcp_manager()

        # Получаем инструменты из MCP конфигурации
        mcp_tools = self.mcp_manager.get_tools_for_agent(config.name)
        self.config.allowed_tools.extend(mcp_tools)

    async def execute_task(self, task: str, context: dict | None = None) -> str:
        """Выполнить задачу через Claude Code SDK"""
        # Создаем опции для SDK
        options = ClaudeCodeOptions(
            model=self.config.model,
            system_prompt=self.config.system_prompt,
            max_turns=self.config.max_turns,
            allowed_tools=self.config.allowed_tools,
            thinking_mode=self.config.thinking_mode,
            permission_mode=self.config.permission_mode,
            working_dir=self.working_dir,
        )

        # Добавляем MCP переменные окружения
        options.env_vars = self.mcp_manager.build_mcp_env(self.config.name)

        # Добавляем контекст к задаче если есть
        if context:
            context_str = "\n\nКонтекст предыдущих операций:\n"
            for key, value in context.items():
                context_str += f"- {key}: {str(value)[:200]}...\n"
            task = task + context_str

        try:
            result = await self.sdk.query(task, options)
            logger.info(f"Agent {self.config.name} completed task successfully")
            return result
        except Exception as e:
            logger.error(f"Agent {self.config.name} failed: {e!s}")
            raise


class MultiModelOrchestrator:
    """Оркестратор для работы с несколькими AI моделями"""

    def __init__(self):
        self.models = {
            "claude": ClaudeCodeAgent,
            "openai": None,  # Будет реализовано
            "local": None,  # Для локальных моделей
        }
        self.agents: dict[str, Any] = {}

    def create_agent(self, agent_type: str, config: AgentConfig):
        """Создать агента определенного типа"""
        if agent_type not in self.models:
            raise ValueError(f"Unknown agent type: {agent_type}")

        agent_class = self.models[agent_type]
        if agent_class:
            self.agents[config.name] = agent_class(config)

    async def collaborate(self, task: str, agents: list[str]) -> dict[str, str]:
        """Выполнить задачу с участием нескольких агентов"""
        results = {}
        context = {}

        for agent_name in agents:
            if agent_name not in self.agents:
                continue

            agent = self.agents[agent_name]
            result = await agent.execute_task(task, context)
            results[agent_name] = result
            context[agent_name] = result

        return results


# Предустановленные конфигурации агентов
AGENT_CONFIGS = {
    "code_reviewer": AgentConfig(
        name="code_reviewer",
        role="Senior Code Reviewer",
        system_prompt="""Вы опытный код-ревьюер. Анализируйте код на:
        1. Уязвимости безопасности (SQL injection, XSS, path traversal)
        2. Производительность и оптимизацию
        3. Читаемость и поддерживаемость
        4. Соответствие PEP 8 и best practices
        5. Потенциальные баги и edge cases

        Используйте memory для отслеживания повторяющихся проблем.""",
        allowed_tools=["Read", "Grep", "Task"],
        max_turns=3,
        thinking_mode=ThinkingMode.THINK,
    ),
    "test_generator": AgentConfig(
        name="test_generator",
        role="Test Engineer",
        system_prompt="""Вы специалист по тестированию. Создавайте:
        1. Unit тесты для всех публичных функций
        2. Integration тесты для API endpoints
        3. Edge cases и error handling
        4. Используйте pytest с fixtures
        5. Покрытие минимум 90%

        Проверяйте документацию через context7 для правильного использования библиотек.""",
        allowed_tools=["Read", "Write", "Edit", "Bash"],
        max_turns=5,
        permission_mode=PermissionMode.ACCEPT_EDITS,
    ),
    "strategy_developer": AgentConfig(
        name="strategy_developer",
        role="Quantitative Developer",
        system_prompt="""Вы разработчик торговых стратегий. Создавайте:
        1. Эффективные торговые алгоритмы
        2. Risk management системы
        3. Backtesting функционал
        4. Performance метрики
        5. Оптимизацию для низкой латентности

        Используйте sequential thinking для сложных алгоритмов.""",
        allowed_tools=["Read", "Write", "Edit", "Bash", "Task"],
        max_turns=10,
        thinking_mode=ThinkingMode.THINK_HARD,
    ),
    "doc_maintainer": AgentConfig(
        name="doc_maintainer",
        role="Technical Writer",
        system_prompt="""Вы технический писатель. Поддерживайте:
        1. API документацию с примерами
        2. README файлы с badges
        3. Docstrings в Google/NumPy стиле
        4. Архитектурные диаграммы
        5. Changelog и migration guides""",
        allowed_tools=["Read", "Write", "Edit"],
        max_turns=3,
    ),
    "autonomous_developer": AgentConfig(
        name="autonomous_developer",
        role="Autonomous Developer",
        system_prompt="""Вы автономный разработчик. Следуйте паттерну:
        1. EXPLORE: Исследуйте кодовую базу через filesystem и grep
        2. PLAN: Создайте план с использованием TodoWrite
        3. IMPLEMENT: Реализуйте решение пошагово
        4. TEST: Создайте и запустите тесты
        5. REFINE: Оптимизируйте на основе результатов

        Работайте полностью самостоятельно. Используйте memory для отслеживания прогресса.""",
        allowed_tools=["Read", "Write", "Edit", "Bash", "Task", "TodoWrite"],
        max_turns=20,
        thinking_mode=ThinkingMode.THINK_HARDER,
        permission_mode=PermissionMode.ACCEPT_EDITS,
    ),
    "performance_optimizer": AgentConfig(
        name="performance_optimizer",
        role="Performance Engineer",
        system_prompt="""Вы специалист по оптимизации. Анализируйте:
        1. Временную и пространственную сложность
        2. Database queries и индексы
        3. Кеширование и мемоизацию
        4. Асинхронность и параллелизм
        5. Профилирование с cProfile/line_profiler

        Измеряйте улучшения количественно.""",
        allowed_tools=["Read", "Edit", "Bash", "Task"],
        max_turns=10,
        thinking_mode=ThinkingMode.ULTRATHINK,
    ),
    "security_auditor": AgentConfig(
        name="security_auditor",
        role="Security Auditor",
        system_prompt="""Вы аудитор безопасности. Проверяйте:
        1. OWASP Top 10 уязвимости
        2. Hardcoded credentials и API keys
        3. Input validation и sanitization
        4. Authentication и authorization
        5. Dependency vulnerabilities

        Создавайте отчеты с CVE ссылками и remediation steps.""",
        allowed_tools=["Read", "Grep", "Task", "Bash"],
        max_turns=5,
        thinking_mode=ThinkingMode.THINK_HARD,
    ),
    "market_analyst": AgentConfig(
        name="market_analyst",
        role="Market Analyst",
        system_prompt="""Вы аналитик финансовых рынков. Анализируйте:
        1. Рыночные тренды и паттерны
        2. Корреляции между активами
        3. Volume profile и order flow
        4. Sentiment analysis
        5. Макроэкономические факторы

        Используйте browser automation для сбора данных.""",
        allowed_tools=["Read", "Write", "Task"],
        max_turns=15,
        thinking_mode=ThinkingMode.THINK,
    ),
}


# Функции для быстрого запуска
async def review_code(file_path: str) -> str:
    """Быстрая проверка кода с использованием code_reviewer агента"""
    orchestrator = MultiModelOrchestrator()
    orchestrator.create_agent("claude", AGENT_CONFIGS["code_reviewer"])

    task = f"Проверьте код в файле {file_path} и предложите улучшения. Обратите внимание на безопасность и производительность."
    results = await orchestrator.collaborate(task, ["code_reviewer"])
    return results.get("code_reviewer", "")


async def generate_tests(file_path: str) -> str:
    """Генерация тестов для файла с использованием test_generator агента"""
    orchestrator = MultiModelOrchestrator()
    orchestrator.create_agent("claude", AGENT_CONFIGS["test_generator"])

    task = f"Создайте comprehensive pytest тесты для {file_path}. Включите unit тесты, edge cases и fixtures."
    results = await orchestrator.collaborate(task, ["test_generator"])
    return results.get("test_generator", "")


async def develop_strategy(description: str) -> str:
    """Разработка новой торговой стратегии с использованием strategy_developer агента"""
    orchestrator = MultiModelOrchestrator()
    orchestrator.create_agent("claude", AGENT_CONFIGS["strategy_developer"])

    task = (
        f"Разработайте торговую стратегию: {description}. Включите risk management и backtesting."
    )
    results = await orchestrator.collaborate(task, ["strategy_developer"])
    return results.get("strategy_developer", "")


async def autonomous_development(feature_description: str) -> str:
    """Автономная разработка функции от идеи до реализации"""
    orchestrator = MultiModelOrchestrator()
    orchestrator.create_agent("claude", AGENT_CONFIGS["autonomous_developer"])

    task = f"""Реализуйте следующую функцию полностью автономно: {feature_description}

    Следуйте паттерну EXPLORE-PLAN-IMPLEMENT-TEST-REFINE.
    Создайте все необходимые файлы, тесты и документацию."""

    results = await orchestrator.collaborate(task, ["autonomous_developer"])
    return results.get("autonomous_developer", "")


async def optimize_performance(file_or_module: str) -> str:
    """Оптимизация производительности кода"""
    orchestrator = MultiModelOrchestrator()
    orchestrator.create_agent("claude", AGENT_CONFIGS["performance_optimizer"])

    task = f"""Проанализируйте и оптимизируйте производительность: {file_or_module}

    Используйте профилирование для измерения улучшений.
    Предложите конкретные оптимизации с метриками."""

    results = await orchestrator.collaborate(task, ["performance_optimizer"])
    return results.get("performance_optimizer", "")


async def security_audit(target_path: str) -> str:
    """Аудит безопасности кода или модуля"""
    orchestrator = MultiModelOrchestrator()
    orchestrator.create_agent("claude", AGENT_CONFIGS["security_auditor"])

    task = f"""Проведите полный аудит безопасности: {target_path}

    Проверьте OWASP Top 10, hardcoded secrets, input validation.
    Создайте детальный отчет с рекомендациями."""

    results = await orchestrator.collaborate(task, ["security_auditor"])
    return results.get("security_auditor", "")


async def collaborative_development(task_description: str, agents: list[str]) -> dict[str, str]:
    """Совместная разработка с участием нескольких агентов"""
    orchestrator = MultiModelOrchestrator()

    # Создаем выбранных агентов
    for agent_name in agents:
        if agent_name in AGENT_CONFIGS:
            orchestrator.create_agent("claude", AGENT_CONFIGS[agent_name])

    # Запускаем совместную работу
    results = await orchestrator.collaborate(task_description, agents)
    return results


if __name__ == "__main__":
    # Пример использования
    async def main():
        # Проверка кода
        result = await review_code("src/main.py")
        print("Code Review:", result)

    asyncio.run(main())
