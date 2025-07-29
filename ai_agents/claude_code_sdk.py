"""
Python обертка для Claude Code SDK
Обеспечивает программный доступ к возможностям Claude Code через Python API
"""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from .utils.token_manager import get_token_manager


class ThinkingMode(Enum):
    """Режимы мышления Claude"""

    NORMAL = "normal"
    THINK = "think"
    THINK_HARD = "think hard"
    THINK_HARDER = "think harder"
    ULTRATHINK = "ultrathink"


class PermissionMode(Enum):
    """Режимы разрешений для редактирования"""

    ACCEPT_EDITS = "acceptEdits"
    BYPASS_PERMISSIONS = "bypassPermissions"
    DEFAULT = "default"
    PLAN = "plan"


@dataclass
class ClaudeCodeOptions:
    """Опции для Claude Code SDK"""

    model: str = "sonnet"  # Можно использовать "opus", "sonnet" или "haiku"
    system_prompt: Optional[str] = None
    max_turns: int = 5
    allowed_tools: List[str] = field(
        default_factory=lambda: ["Read", "Write", "Edit", "Bash", "Task"]
    )
    permission_mode: PermissionMode = PermissionMode.DEFAULT
    thinking_mode: ThinkingMode = ThinkingMode.NORMAL
    timeout: int = 300000  # 5 минут по умолчанию
    working_dir: Optional[Path] = None
    env_vars: Dict[str, str] = field(default_factory=dict)

    def to_cli_args(self) -> List[str]:
        """Преобразовать опции в аргументы CLI"""
        args = [
            "--model",
            self.model,
            "--max-turns",
            str(self.max_turns),
            "--permission-mode",
            self.permission_mode.value,
        ]

        if self.system_prompt:
            args.extend(["--system-prompt", self.system_prompt])

        if self.thinking_mode != ThinkingMode.NORMAL:
            args.extend(["--thinking-mode", self.thinking_mode.value])

        for tool in self.allowed_tools:
            args.extend(["--allowedTools", tool])

        return args


class ClaudeCodeSDK:
    """Python SDK для Claude Code"""

    def __init__(self, use_package_auth: bool = True):
        """
        Инициализация SDK

        Args:
            use_package_auth: True для использования пакетной авторизации через Claude CLI,
                            False для использования API ключа (legacy)
        """
        self.use_package_auth = use_package_auth
        self.api_key = None
        self.claude_cmd = self._find_claude_cli()

        if not use_package_auth:
            # Legacy режим с API ключом
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ValueError(
                    "API key required when use_package_auth=False. Set ANTHROPIC_API_KEY environment variable"
                )
        else:
            # Проверяем что Claude CLI авторизован
            self._verify_claude_auth()

        self._sessions: Dict[str, Any] = {}
        self.token_manager = get_token_manager()

    def _find_claude_cli(self) -> str:
        """Найти путь к Claude CLI"""
        claude_paths = [
            "/Users/ruslan/.claude/local/claude",  # Стандартный путь установки
            os.path.expanduser("~/.claude/local/claude"),  # Универсальный путь
            "claude",  # Если в PATH
        ]

        for path in claude_paths:
            if os.path.exists(path):
                return path
            # Проверяем через which
            try:
                result = subprocess.run(["which", path], capture_output=True, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                continue

        # Если не нашли, используем дефолтный
        return "claude"

    def _verify_claude_auth(self):
        """Проверить что Claude CLI авторизован"""
        try:
            process = subprocess.run(
                [self.claude_cmd, "config", "list"],
                capture_output=True,
                text=True,
                check=True,
            )

            # Проверяем что конфигурация существует
            config = json.loads(process.stdout)
            if not config:
                raise ValueError(
                    "Claude CLI not configured. Run 'claude' first to authenticate."
                )

        except subprocess.CalledProcessError:
            raise ValueError(
                "Claude CLI not available or not authenticated. Please run 'claude' to authenticate."
            )
        except json.JSONDecodeError:
            raise ValueError("Invalid Claude CLI configuration.")

    async def query(
        self,
        prompt: str,
        options: Optional[ClaudeCodeOptions] = None,
        agent_name: str = "unknown",
    ) -> str:
        """Выполнить одиночный запрос к Claude Code"""
        options = options or ClaudeCodeOptions()

        # Проверяем кеш
        cached_result = self.token_manager.cache.get(prompt)
        if cached_result:
            # Записываем использование кешированного результата
            prompt_tokens = self.token_manager.count_tokens(prompt, options.model)
            completion_tokens = self.token_manager.count_tokens(
                cached_result, options.model
            )

            self.token_manager.record_usage(
                model=options.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                agent=agent_name,
                cached=True,
            )

            return cached_result

        # Оценка стоимости и проверка бюджета
        estimated_tokens = self.token_manager.count_tokens(prompt, options.model)
        estimated_tokens += 500  # Ожидаемый ответ

        can_afford, reason = self.token_manager.can_afford(estimated_tokens)
        if not can_afford:
            raise Exception(f"Token budget exceeded: {reason}")

        cmd = [self.claude_cmd] + options.to_cli_args()

        env = os.environ.copy()

        # Добавляем API ключ только в legacy режиме
        if not self.use_package_auth and self.api_key:
            env["ANTHROPIC_API_KEY"] = self.api_key

        env.update(options.env_vars)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=options.working_dir or Path.cwd(),
            env=env,
        )

        stdout, stderr = await process.communicate(input=prompt.encode())

        if process.returncode != 0:
            raise Exception(f"Claude Code error: {stderr.decode()}")

        result = stdout.decode()

        # Сохраняем в кеш
        self.token_manager.cache.set(prompt, result)

        # Записываем фактическое использование токенов
        prompt_tokens = self.token_manager.count_tokens(prompt, options.model)
        completion_tokens = self.token_manager.count_tokens(result, options.model)

        self.token_manager.record_usage(
            model=options.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            agent=agent_name,
            cached=False,
        )

        return result

    async def stream(
        self, prompt: str, options: Optional[ClaudeCodeOptions] = None
    ) -> AsyncIterator[str]:
        """Потоковое выполнение запроса с получением результатов в реальном времени"""
        options = options or ClaudeCodeOptions()

        cmd = ["claude", "--sse"] + options.to_cli_args() + [prompt]

        env = os.environ.copy()
        env["ANTHROPIC_API_KEY"] = self.api_key
        env.update(options.env_vars)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=options.working_dir or Path.cwd(),
            env=env,
        )

        async for line in process.stdout:
            decoded = line.decode().strip()
            if decoded.startswith("data: "):
                yield decoded[6:]

    async def batch(
        self, tasks: List[Dict[str, Any]], parallel: bool = True
    ) -> List[str]:
        """Выполнить несколько задач пакетно"""
        if parallel:
            results = await asyncio.gather(
                *[self.query(task["prompt"], task.get("options")) for task in tasks]
            )
        else:
            results = []
            for task in tasks:
                result = await self.query(task["prompt"], task.get("options"))
                results.append(result)

        return results

    def create_session(
        self, session_id: str, options: ClaudeCodeOptions
    ) -> "ClaudeSession":
        """Создать сессию для последовательных запросов с сохранением контекста"""
        session = ClaudeSession(self, session_id, options)
        self._sessions[session_id] = session
        return session

    def get_token_usage(self, period: str = "daily") -> Dict[str, Any]:
        """Получить отчет об использовании токенов"""
        return self.token_manager.get_usage_report(period)


class ClaudeSession:
    """Сессия для последовательных запросов с сохранением контекста"""

    def __init__(self, sdk: ClaudeCodeSDK, session_id: str, options: ClaudeCodeOptions):
        self.sdk = sdk
        self.session_id = session_id
        self.options = options
        self.history: List[Dict[str, str]] = []
        self.context: Dict[str, Any] = {}

    async def query(self, prompt: str) -> str:
        """Выполнить запрос в рамках сессии"""
        # Добавляем контекст из истории
        if self.history:
            context_prompt = self._build_context_prompt(prompt)
        else:
            context_prompt = prompt

        result = await self.sdk.query(context_prompt, self.options)

        # Сохраняем в истории
        self.history.append(
            {
                "prompt": prompt,
                "response": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return result

    def _build_context_prompt(self, prompt: str) -> str:
        """Построить промпт с учетом контекста"""
        context_lines = ["Продолжаем работу над задачей. Предыдущие действия:"]

        # Берем последние 3 взаимодействия для контекста
        for item in self.history[-3:]:
            context_lines.append(f"- {item['prompt'][:100]}...")

        context_lines.append(f"\nТекущая задача: {prompt}")

        return "\n".join(context_lines)


class ClaudeAgentBuilder:
    """Билдер для создания специализированных агентов"""

    def __init__(self, sdk: ClaudeCodeSDK):
        self.sdk = sdk

    def create_code_reviewer(self) -> ClaudeCodeOptions:
        """Создать агента для код-ревью"""
        return ClaudeCodeOptions(
            system_prompt="""Вы старший код-ревьюер. Анализируйте код на:
            1. Уязвимости безопасности (SQL injection, XSS, и т.д.)
            2. Производительность и оптимизацию
            3. Читаемость и поддерживаемость
            4. Соответствие PEP 8 и best practices
            5. Потенциальные баги и edge cases

            Предоставляйте конкретные предложения по улучшению.""",
            allowed_tools=["Read", "Grep", "Task"],
            thinking_mode=ThinkingMode.THINK,
            max_turns=3,
        )

    def create_test_generator(self) -> ClaudeCodeOptions:
        """Создать агента для генерации тестов"""
        return ClaudeCodeOptions(
            system_prompt="""Вы специалист по тестированию. Создавайте:
            1. Unit тесты для всех публичных функций
            2. Integration тесты для API endpoints
            3. Edge cases и error handling
            4. Используйте pytest и fixtures
            5. Покрытие должно быть не менее 90%""",
            allowed_tools=["Read", "Write", "Edit", "Bash"],
            thinking_mode=ThinkingMode.NORMAL,
            max_turns=5,
        )

    def create_autonomous_developer(self) -> ClaudeCodeOptions:
        """Создать агента автономной разработки"""
        return ClaudeCodeOptions(
            system_prompt="""Вы автономный разработчик. Следуйте паттерну:
            1. EXPLORE: Исследуйте кодовую базу и понимайте контекст
            2. PLAN: Создайте детальный план реализации
            3. IMPLEMENT: Реализуйте решение пошагово
            4. TEST: Протестируйте реализацию
            5. REFINE: Улучшите код на основе тестов

            Работайте самостоятельно до полного завершения задачи.""",
            allowed_tools=["Read", "Write", "Edit", "Bash", "Task", "TodoWrite"],
            thinking_mode=ThinkingMode.THINK_HARD,
            max_turns=20,
            permission_mode=PermissionMode.ACCEPT_EDITS,
        )

    def create_performance_optimizer(self) -> ClaudeCodeOptions:
        """Создать агента оптимизации производительности"""
        return ClaudeCodeOptions(
            system_prompt="""Вы специалист по оптимизации. Анализируйте:
            1. Временную сложность алгоритмов
            2. Использование памяти
            3. Database queries и N+1 проблемы
            4. Асинхронность и параллелизм
            5. Кеширование и мемоизацию

            Используйте профилирование для измерения улучшений.""",
            allowed_tools=["Read", "Edit", "Bash", "Task"],
            thinking_mode=ThinkingMode.THINK_HARDER,
            max_turns=10,
        )


# Вспомогательные функции для быстрого доступа
async def quick_review(file_path: str, api_key: Optional[str] = None) -> str:
    """Быстрая проверка кода файла"""
    sdk = ClaudeCodeSDK(api_key)
    builder = ClaudeAgentBuilder(sdk)
    options = builder.create_code_reviewer()

    prompt = f"Проверьте код в файле {file_path} и предложите улучшения"
    return await sdk.query(prompt, options)


async def generate_tests(file_path: str, api_key: Optional[str] = None) -> str:
    """Генерация тестов для файла"""
    sdk = ClaudeCodeSDK(api_key)
    builder = ClaudeAgentBuilder(sdk)
    options = builder.create_test_generator()

    prompt = f"Создайте comprehensive pytest тесты для {file_path}"
    return await sdk.query(prompt, options)


async def implement_feature(description: str, api_key: Optional[str] = None) -> str:
    """Автономная реализация функции"""
    sdk = ClaudeCodeSDK(api_key)
    builder = ClaudeAgentBuilder(sdk)
    options = builder.create_autonomous_developer()

    prompt = f"Реализуйте следующую функцию: {description}"
    return await sdk.query(prompt, options)


if __name__ == "__main__":
    # Пример использования
    async def main():
        sdk = ClaudeCodeSDK()

        # Простой запрос
        result = await sdk.query("Объясните, как работает async/await в Python")
        print("Simple query:", result[:200], "...")

        # Сессия с контекстом
        session = sdk.create_session(
            "dev_session",
            ClaudeCodeOptions(thinking_mode=ThinkingMode.THINK, max_turns=10),
        )

        await session.query("Создайте класс для управления торговыми ордерами")
        await session.query("Добавьте методы для risk management")

        # Пакетная обработка
        tasks = [
            {"prompt": "Проверьте файл main.py"},
            {"prompt": "Создайте тесты для exchange.py"},
            {"prompt": "Оптимизируйте strategy.py"},
        ]

        results = await sdk.batch(tasks, parallel=True)

        print(f"Token usage today: {sdk.get_token_usage()}")

    asyncio.run(main())
