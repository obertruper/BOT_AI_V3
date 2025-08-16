#!/usr/bin/env python3
"""
Автоматизированная система кросс-верификации с тремя AI системами
Workflow: задача → 3 чата → кросс-отчет → feedback → итерация

Автор: BOT Trading v3 Team
Дата: 13 июля 2025
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

# Настройка логгера
logger = logging.getLogger(__name__)

# MCP функции - импортируем динамически для гибкости
try:
    import sys

    # Список MCP функций которые нам нужны
    MCP_FUNCTIONS = [
        "mcp__playwright__browser_navigate",
        "mcp__playwright__browser_take_screenshot",
        "mcp__playwright__browser_click",
        "mcp__playwright__browser_type",
        "mcp__playwright__browser_tab_new",
        "mcp__playwright__browser_tab_list",
        "mcp__playwright__browser_tab_select",
        "mcp__playwright__browser_snapshot",
        "mcp__playwright__browser_press_key",
    ]

    # Проверяем доступность MCP функций
    MCP_AVAILABLE = True
    for func_name in MCP_FUNCTIONS:
        try:
            globals()[func_name] = getattr(sys.modules["__main__"], func_name)
        except (AttributeError, KeyError):
            MCP_AVAILABLE = False
            logger.warning(f"MCP функция {func_name} недоступна")

except Exception as e:
    MCP_AVAILABLE = False
    logger.error(f"Ошибка импорта MCP функций: {e}")


@dataclass
class ChatSession:
    """Информация о чат-сессии с AI системой"""

    ai_system: str
    chat_id: str
    url: str
    tab_index: int
    status: str = "created"
    created_at: datetime = None
    responses: list[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if self.responses is None:
            self.responses = []


@dataclass
class CrossVerificationTask:
    """Задача для кросс-верификации"""

    task_id: str
    description: str
    task_content: str
    ai_systems: list[str]
    chat_sessions: dict[str, ChatSession]
    cross_report_path: str = None
    iteration_count: int = 0
    status: str = "created"
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC)
        if not self.chat_sessions:
            self.chat_sessions = {}


class AutomatedCrossVerification:
    """Автоматизированная система кросс-верификации"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "ai_agents/configs/cross_verification_config.yaml"
        self.sessions_path = "ai_agents/configs/active_sessions.json"
        self.reports_dir = Path("docs/AI_VERIFICATION_REPORTS")
        self.reports_dir.mkdir(exist_ok=True)

        self.config = self._load_config()
        self.active_sessions = self._load_active_sessions()

        # AI системы и их конфигурация
        self.ai_systems = {
            "chatgpt": {
                "url": "https://chatgpt.com",
                "name": "ChatGPT o3-pro",
                "prompt_prefix": "Ты эксперт в разработке торговых ботов и криптотрейдинге. ",
                "new_chat_button": "[data-testid='new-chat-button']",
            },
            "grok": {
                "url": "https://grok.com",
                "name": "Grok v4",
                "prompt_prefix": "Ты AI-консультант по алготрейдингу и финтех разработке. ",
                "new_chat_button": "button[aria-label='New chat']",
            },
            "claude": {
                "url": "https://claude.ai",
                "name": "Claude Opus 4",
                "prompt_prefix": "Ты архитектор торговых систем и эксперт по Python разработке. ",
                "new_chat_button": "[data-testid='new-conversation-button']",
            },
        }

    def _load_config(self) -> dict:
        """Загрузка конфигурации"""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Создаем дефолтную конфигурацию
            default_config = {
                "workflow": {
                    "max_iterations": 5,
                    "auto_save_sessions": True,
                    "screenshot_on_error": True,
                    "parallel_processing": True,
                },
                "ai_systems": ["chatgpt", "grok", "claude"],
                "timeouts": {"page_load": 30, "response_wait": 120, "click_wait": 5},
                "reports": {
                    "auto_generate": True,
                    "include_screenshots": True,
                    "format": "markdown",
                },
            }

            # Создаем папку configs если не существует
            Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

            return default_config

    def _load_active_sessions(self) -> dict:
        """Загрузка активных сессий"""
        try:
            with open(self.sessions_path, encoding="utf-8") as f:
                data = json.load(f)
                # Восстанавливаем объекты ChatSession
                sessions = {}
                for task_id, task_data in data.items():
                    chat_sessions = {}
                    for ai_system, session_data in task_data.get("chat_sessions", {}).items():
                        session_data["created_at"] = datetime.fromisoformat(
                            session_data["created_at"]
                        )
                        chat_sessions[ai_system] = ChatSession(**session_data)

                    task_data["created_at"] = datetime.fromisoformat(task_data["created_at"])
                    task_data["chat_sessions"] = chat_sessions
                    sessions[task_id] = CrossVerificationTask(**task_data)

                return sessions
        except FileNotFoundError:
            return {}

    def _save_active_sessions(self):
        """Сохранение активных сессий"""
        # Конвертируем объекты в JSON-совместимый формат
        data = {}
        for task_id, task in self.active_sessions.items():
            task_dict = asdict(task)
            # Конвертируем datetime в string
            task_dict["created_at"] = task.created_at.isoformat()
            for ai_system, session in task_dict["chat_sessions"].items():
                session["created_at"] = session["created_at"].isoformat()
            data[task_id] = task_dict

        # Создаем папку если не существует
        Path(self.sessions_path).parent.mkdir(parents=True, exist_ok=True)

        with open(self.sessions_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    async def create_cross_verification_task(
        self, description: str, task_content: str, ai_systems: list[str] = None
    ) -> str:
        """
        Создание новой задачи кросс-верификации

        Args:
            description: Описание задачи
            task_content: Содержание задачи для отправки AI
            ai_systems: Список AI систем (по умолчанию все)

        Returns:
            task_id: Уникальный ID задачи
        """
        task_id = f"cross_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if ai_systems is None:
            ai_systems = self.config.get("ai_systems", ["chatgpt", "grok", "claude"])

        task = CrossVerificationTask(
            task_id=task_id,
            description=description,
            task_content=task_content,
            ai_systems=ai_systems,
            chat_sessions={},
        )

        self.active_sessions[task_id] = task
        self._save_active_sessions()

        logger.info(f"Создана задача кросс-верификации: {task_id}")
        return task_id

    async def initialize_ai_chats(self, task_id: str) -> dict[str, ChatSession]:
        """
        Инициализация чатов со всеми AI системами

        Args:
            task_id: ID задачи

        Returns:
            Dict с ChatSession для каждой AI системы
        """
        if task_id not in self.active_sessions:
            raise ValueError(f"Задача {task_id} не найдена")

        task = self.active_sessions[task_id]

        logger.info(f"Инициализация чатов для задачи {task_id}")

        # Параллельно открываем все AI системы
        if self.config.get("workflow", {}).get("parallel_processing", True):
            await asyncio.gather(
                *[self._initialize_single_chat(task, ai_system) for ai_system in task.ai_systems]
            )
        else:
            # Последовательно
            for ai_system in task.ai_systems:
                await self._initialize_single_chat(task, ai_system)

        self._save_active_sessions()
        return task.chat_sessions

    async def _initialize_single_chat(self, task: CrossVerificationTask, ai_system: str):
        """Инициализация одного чата с AI системой"""
        if ai_system not in self.ai_systems:
            raise ValueError(f"Неизвестная AI система: {ai_system}")

        ai_config = self.ai_systems[ai_system]

        try:
            # Проверяем доступность MCP функций
            if not MCP_AVAILABLE:
                logger.warning(f"MCP функции недоступны для {ai_system}")
                current_tab = -1
            else:
                # Открываем новую вкладку
                await globals()["mcp__playwright__browser_tab_new"](url=ai_config["url"])

                # Получаем список вкладок для определения индекса
                tabs = await globals()["mcp__playwright__browser_tab_list"]()
                current_tab = len(tabs) - 1

                # Ждем загрузки страницы
                await asyncio.sleep(self.config.get("timeouts", {}).get("page_load", 30))

                # Делаем скриншот для диагностики
                screenshot_path = f"ai_chats_{ai_system}_{task.task_id}.png"
                await globals()["mcp__playwright__browser_take_screenshot"](
                    filename=screenshot_path
                )

                # Создаем новый чат (если нужно)
                try:
                    snapshot = await globals()["mcp__playwright__browser_snapshot"]()
                    # Ищем кнопку создания нового чата в snapshot
                    if "new" in snapshot.lower() and "chat" in snapshot.lower():
                        # Кликаем на кнопку нового чата
                        await globals()["mcp__playwright__browser_click"](
                            element="New chat button", ref=ai_config["new_chat_button"]
                        )
                    await asyncio.sleep(self.config.get("timeouts", {}).get("click_wait", 5))
                except Exception as e:
                    logger.warning(f"Не удалось создать новый чат для {ai_system}: {e}")

            # Извлекаем chat ID из URL
            current_url = "placeholder_url"  # В реальности получаем из браузера
            chat_id = self._extract_chat_id(current_url, ai_system)

            # Создаем объект сессии
            session = ChatSession(
                ai_system=ai_system,
                chat_id=chat_id,
                url=current_url,
                tab_index=current_tab,
                status="initialized",
            )

            task.chat_sessions[ai_system] = session

            logger.info(f"Инициализирован чат {ai_system}: {chat_id}")

        except Exception as e:
            logger.error(f"Ошибка инициализации чата {ai_system}: {e}")
            # Создаем сессию с ошибкой для отслеживания
            session = ChatSession(
                ai_system=ai_system,
                chat_id="error",
                url="error",
                tab_index=-1,
                status="error",
            )
            task.chat_sessions[ai_system] = session

    def _extract_chat_id(self, url: str, ai_system: str) -> str:
        """Извлечение chat ID из URL"""
        try:
            parsed_url = urlparse(url)

            if ai_system == "chatgpt":
                # ChatGPT: https://chatgpt.com/c/chat-id
                if "/c/" in parsed_url.path:
                    return parsed_url.path.split("/c/")[-1]
            elif ai_system == "grok":
                # Grok: https://grok.com/chat/chat-id
                if "/chat/" in parsed_url.path:
                    return parsed_url.path.split("/chat/")[-1]
            elif ai_system == "claude":
                # Claude: https://claude.ai/chat/chat-id
                if "/chat/" in parsed_url.path:
                    return parsed_url.path.split("/chat/")[-1]

            # Fallback: использовать весь path как ID
            return parsed_url.path.replace("/", "_")

        except Exception as e:
            logger.warning(f"Не удалось извлечь chat ID из {url}: {e}")
            return f"unknown_{datetime.now().strftime('%H%M%S')}"

    async def send_task_to_all_chats(
        self, task_id: str, expected_length: str = "long"
    ) -> dict[str, str]:
        """
        Отправка задачи во все инициализированные чаты с умным сбором ответов

        Args:
            task_id: ID задачи
            expected_length: Ожидаемая длина ответов (short/medium/long/very_long)

        Returns:
            Dict с ответами от каждой AI системы
        """
        if task_id not in self.active_sessions:
            raise ValueError(f"Задача {task_id} не найдена")

        task = self.active_sessions[task_id]

        logger.info(f"Отправка задачи {task_id} во все чаты (ожидаем {expected_length} ответы)")

        # Используем улучшенную систему сбора ответов
        try:
            from ai_agents.response_collector import EnhancedResponseHandler

            enhanced_handler = EnhancedResponseHandler()

            # Сначала отправляем запросы
            await self._send_prompts_to_chats(task)

            # Затем умно собираем ответы
            responses = await enhanced_handler.enhanced_send_task_to_all_chats(
                task, expected_length
            )

            logger.info(f"Собраны ответы от {len(responses)} AI систем")
            for ai_system, response in responses.items():
                word_count = len(response.split())
                logger.info(f"{ai_system}: {word_count} слов")

        except ImportError:
            logger.warning("Улучшенная система сбора недоступна, используем базовую")
            responses = await self._basic_response_collection(task)

        self._save_active_sessions()
        return responses

    async def _send_prompts_to_chats(self, task):
        """Отправка промптов во все чаты"""
        logger.info("Отправка промптов во все активные чаты")

        # Параллельно отправляем в все чаты
        if self.config.get("workflow", {}).get("parallel_processing", True):
            await asyncio.gather(
                *[
                    self._send_prompt_to_single_chat(task, ai_system)
                    for ai_system in task.ai_systems
                    if ai_system in task.chat_sessions
                    and task.chat_sessions[ai_system].status != "error"
                ],
                return_exceptions=True,
            )
        else:
            # Последовательно
            for ai_system in task.ai_systems:
                if (
                    ai_system in task.chat_sessions
                    and task.chat_sessions[ai_system].status != "error"
                ):
                    await self._send_prompt_to_single_chat(task, ai_system)

    async def _send_prompt_to_single_chat(self, task, ai_system: str):
        """Отправка промпта в один чат (без ожидания ответа)"""
        session = task.chat_sessions[ai_system]
        ai_config = self.ai_systems[ai_system]

        # Переключаемся на нужную вкладку
        if MCP_AVAILABLE:
            await globals()["mcp__playwright__browser_tab_select"](index=session.tab_index)
        else:
            logger.warning(f"MCP функции недоступны для переключения на вкладку {ai_system}")

        # Формируем полный промпт
        full_prompt = (
            f"{ai_config['prompt_prefix']}"
            f"Задача: {task.description}\n\n"
            f"{task.task_content}\n\n"
            f"Отвечай подробно и структурированно."
        )

        # Ищем поле ввода и отправляем сообщение

        # Отправляем промпт
        if MCP_AVAILABLE:
            await globals()["mcp__playwright__browser_type"](
                element="Message input field",
                ref="textarea",  # Универсальный селектор
                text=full_prompt,
                submit=True,
            )
        else:
            logger.warning(f"MCP функции недоступны для отправки промпта в {ai_system}")

        logger.info(f"Промпт отправлен в {ai_system}")

    async def _basic_response_collection(self, task) -> dict[str, str]:
        """Базовая система сбора ответов (fallback)"""
        responses = {}

        # Ждем ответов
        await asyncio.sleep(self.config.get("timeouts", {}).get("response_wait", 120))

        # Собираем ответы
        for ai_system in task.ai_systems:
            if ai_system in task.chat_sessions and task.chat_sessions[ai_system].status != "error":
                try:
                    session = task.chat_sessions[ai_system]

                    # Переключаемся на вкладку
                    if MCP_AVAILABLE:
                        await globals()["mcp__playwright__browser_tab_select"](
                            index=session.tab_index
                        )
                    else:
                        logger.warning(f"MCP функции недоступны для {ai_system}")

                    # Получаем snapshot
                    if MCP_AVAILABLE:
                        snapshot = await globals()["mcp__playwright__browser_snapshot"]()
                    else:
                        snapshot = "MCP недоступен"

                    # Извлекаем ответ (упрощенно)
                    response = self._extract_ai_response(snapshot, ai_system)
                    responses[ai_system] = response

                    # Сохраняем в сессию
                    session.responses.append(response)
                    session.status = "responded"

                except Exception as e:
                    logger.error(f"Ошибка сбора ответа от {ai_system}: {e}")
                    responses[ai_system] = f"ERROR: {e}"

        return responses

    async def _send_to_single_chat(self, task: CrossVerificationTask, ai_system: str) -> str:
        """Отправка задачи в один чат"""
        session = task.chat_sessions[ai_system]
        ai_config = self.ai_systems[ai_system]

        # Переключаемся на нужную вкладку
        if MCP_AVAILABLE:
            await globals()["mcp__playwright__browser_tab_select"](index=session.tab_index)
        else:
            logger.warning("MCP функции недоступны")

        # Формируем полный промпт
        full_prompt = (
            f"{ai_config['prompt_prefix']}"
            f"Задача: {task.description}\n\n"
            f"{task.task_content}\n\n"
            f"Отвечай подробно и структурированно."
        )

        # Ищем поле ввода и отправляем сообщение
        if MCP_AVAILABLE:
            snapshot = await globals()["mcp__playwright__browser_snapshot"]()
        else:
            snapshot = "MCP недоступен"

        # Ищем текстовое поле в snapshot
        # В реальности здесь будет поиск конкретных элементов
        text_input_ref = "textarea"  # Placeholder

        if MCP_AVAILABLE:
            await globals()["mcp__playwright__browser_type"](
                element="Message input field",
                ref=text_input_ref,
                text=full_prompt,
                submit=True,
            )
        else:
            logger.warning("MCP функции недоступны для отправки сообщения")

        # Ждем ответа
        await asyncio.sleep(self.config.get("timeouts", {}).get("response_wait", 120))

        # Получаем ответ из snapshot
        if MCP_AVAILABLE:
            response_snapshot = await globals()["mcp__playwright__browser_snapshot"]()
        else:
            response_snapshot = "MCP недоступен"

        # Извлекаем ответ AI (здесь нужна более сложная логика парсинга)
        response = self._extract_ai_response(response_snapshot, ai_system)

        logger.info(f"Получен ответ от {ai_system} ({len(response)} символов)")
        return response

    def _extract_ai_response(self, snapshot: str, ai_system: str) -> str:
        """Извлечение ответа AI из snapshot"""
        # Здесь будет более сложная логика парсинга ответов
        # Пока возвращаем placeholder
        return f"Ответ от {ai_system} получен. [Snapshot: {len(snapshot)} символов]"

    async def generate_cross_report(self, task_id: str) -> str:
        """
        Генерация кросс-верификационного отчета

        Args:
            task_id: ID задачи

        Returns:
            Путь к созданному отчету
        """
        if task_id not in self.active_sessions:
            raise ValueError(f"Задача {task_id} не найдена")

        task = self.active_sessions[task_id]

        # Создаем отчет
        report_filename = f"{task_id.upper()}_CROSS_VERIFICATION.md"
        report_path = self.reports_dir / report_filename

        # Генерируем содержимое отчета
        report_content = self._generate_report_content(task)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        task.cross_report_path = str(report_path)
        self._save_active_sessions()

        logger.info(f"Создан кросс-верификационный отчет: {report_path}")
        return str(report_path)

    def _generate_report_content(self, task: CrossVerificationTask) -> str:
        """Генерация содержимого отчета"""
        now = datetime.now().strftime("%d %B %Y, %H:%M")

        content = f"""# Кросс-верификация: {task.description}

**Дата**: {now}
**Задача ID**: {task.task_id}
**Итерация**: {task.iteration_count + 1}
**Статус**: {task.status}

## Описание задачи

{task.description}

### Содержание задачи
```
{task.task_content}
```

---

"""

        # Добавляем ответы от каждой AI системы
        for i, ai_system in enumerate(task.ai_systems, 1):
            ai_config = self.ai_systems.get(ai_system, {})
            ai_name = ai_config.get("name", ai_system.title())

            content += f"## {i}. {ai_name}: Экспертная консультация\n\n"

            if ai_system in task.chat_sessions:
                session = task.chat_sessions[ai_system]
                content += f"**Статус**: {session.status}  \n"
                content += f"**Chat ID**: {session.chat_id}  \n"
                content += f"**URL**: {session.url}  \n\n"

                if session.responses:
                    content += "### Ответ AI системы\n\n"
                    content += session.responses[-1]  # Последний ответ
                else:
                    content += "*Ответ не получен*\n"
            else:
                content += "*Сессия не инициализирована*\n"

            content += "\n---\n\n"

        # Добавляем анализ и синтез
        content += """## Кросс-верификационный анализ

### Сравнение подходов

| AI Система | Статус | Ключевые рекомендации |
|------------|--------|----------------------|
"""

        for ai_system in task.ai_systems:
            ai_name = self.ai_systems.get(ai_system, {}).get("name", ai_system.title())
            if ai_system in task.chat_sessions:
                session = task.chat_sessions[ai_system]
                status = "✅ Завершено" if session.status == "responded" else "❌ Ошибка"
                recommendations = "Анализ получен" if session.responses else "Нет данных"
            else:
                status = "❌ Не инициализирован"
                recommendations = "Нет данных"

            content += f"| **{ai_name}** | {status} | {recommendations} |\n"

        content += f"""

### Синтезированные рекомендации

*[Будет заполнено после анализа всех ответов]*

---

**Последнее обновление**: {now}
**Статус документа**: 🔄 В процессе
**Следующий этап**: Feedback итерация
"""

        return content

    async def send_cross_report_for_feedback(self, task_id: str) -> dict[str, str]:
        """
        Отправка кросс-отчета обратно в AI системы для получения feedback

        Args:
            task_id: ID задачи

        Returns:
            Dict с feedback от каждой AI системы
        """
        if task_id not in self.active_sessions:
            raise ValueError(f"Задача {task_id} не найдена")

        task = self.active_sessions[task_id]

        if not task.cross_report_path:
            raise ValueError(f"Кросс-отчет не создан для задачи {task_id}")

        # Читаем содержимое отчета
        with open(task.cross_report_path, encoding="utf-8") as f:
            report_content = f.read()

        # Формируем feedback промпт
        feedback_prompt = f"""
Проанализируй этот кросс-верификационный отчет от трех AI систем и дай свою экспертную оценку:

{report_content}

Твоя задача:
1. Оценить качество рекомендаций от всех трех систем
2. Найти сильные и слабые стороны каждого подхода
3. Предложить улучшения и дополнения
4. Указать что нужно доработать или изменить
5. Дать финальные рекомендации для реализации

Отвечай структурированно и конкретно.
"""

        # Временно изменяем содержимое задачи для feedback
        original_content = task.task_content
        task.task_content = feedback_prompt

        # Отправляем во все чаты
        feedback_responses = await self.send_task_to_all_chats(task_id)

        # Восстанавливаем оригинальное содержимое
        task.task_content = original_content

        # Увеличиваем счетчик итераций
        task.iteration_count += 1
        task.status = "feedback_received"

        self._save_active_sessions()

        logger.info(f"Получен feedback по отчету для задачи {task_id}")
        return feedback_responses

    async def run_full_workflow(
        self, description: str, task_content: str, max_iterations: int = None
    ) -> tuple[str, str]:
        """
        Запуск полного workflow кросс-верификации

        Args:
            description: Описание задачи
            task_content: Содержание задачи
            max_iterations: Максимальное количество итераций

        Returns:
            Tuple (task_id, final_report_path)
        """
        if max_iterations is None:
            max_iterations = self.config.get("workflow", {}).get("max_iterations", 5)

        logger.info(f"Запуск полного workflow: {description}")

        # 1. Создаем задачу
        task_id = await self.create_cross_verification_task(description, task_content)

        # 2. Инициализируем чаты
        await self.initialize_ai_chats(task_id)

        # 3. Отправляем задачу
        responses = await self.send_task_to_all_chats(task_id)

        # 4. Генерируем кросс-отчет
        report_path = await self.generate_cross_report(task_id)

        # 5. Итерации feedback
        for iteration in range(max_iterations - 1):
            logger.info(f"Итерация feedback {iteration + 1}/{max_iterations - 1}")

            try:
                feedback = await self.send_cross_report_for_feedback(task_id)

                # Обновляем отчет с feedback
                updated_report = await self.generate_cross_report(task_id)

                # Проверяем критерии остановки
                if self._should_stop_iterations(feedback):
                    logger.info("Достигнута сходимость, останавливаем итерации")
                    break

            except Exception as e:
                logger.error(f"Ошибка в итерации {iteration + 1}: {e}")
                break

        # Финализируем
        task = self.active_sessions[task_id]
        task.status = "completed"
        self._save_active_sessions()

        logger.info(f"Workflow завершен для задачи {task_id}")
        return task_id, task.cross_report_path

    def _should_stop_iterations(self, feedback: dict[str, str]) -> bool:
        """Проверка критериев остановки итераций"""
        # Простая эвристика: если все AI системы дают короткие ответы,
        # значит больше нечего добавить
        avg_length = sum(len(response) for response in feedback.values()) / len(feedback)
        return avg_length < 500  # Менее 500 символов в среднем

    def get_task_status(self, task_id: str) -> dict:
        """Получение статуса задачи"""
        if task_id not in self.active_sessions:
            return {"error": f"Задача {task_id} не найдена"}

        task = self.active_sessions[task_id]
        return {
            "task_id": task.task_id,
            "description": task.description,
            "status": task.status,
            "iteration_count": task.iteration_count,
            "ai_systems": task.ai_systems,
            "chat_sessions": {
                ai_system: {
                    "status": session.status,
                    "chat_id": session.chat_id,
                    "responses_count": len(session.responses),
                }
                for ai_system, session in task.chat_sessions.items()
            },
            "cross_report_path": task.cross_report_path,
            "created_at": task.created_at.isoformat(),
        }

    def list_active_tasks(self) -> list[dict]:
        """Список всех активных задач"""
        return [
            {
                "task_id": task.task_id,
                "description": task.description,
                "status": task.status,
                "iteration_count": task.iteration_count,
                "created_at": task.created_at.isoformat(),
            }
            for task in self.active_sessions.values()
        ]


# CLI интерфейс
async def main():
    """Основная функция для CLI запуска"""
    import sys

    if len(sys.argv) < 3:
        print("Использование: python automated_cross_verification.py <description> <task_content>")
        print(
            "Пример: python automated_cross_verification.py 'Стратегия скальпинга' 'Разработай стратегию скальпинга для BTC'"
        )
        sys.exit(1)

    description = sys.argv[1]
    task_content = sys.argv[2]

    # Создаем систему
    cross_verifier = AutomatedCrossVerification()

    # Запускаем полный workflow
    task_id, report_path = await cross_verifier.run_full_workflow(description, task_content)

    print("✅ Workflow завершен!")
    print(f"📋 Task ID: {task_id}")
    print(f"📄 Отчет: {report_path}")

    # Показываем статус
    status = cross_verifier.get_task_status(task_id)
    print(f"📊 Итераций: {status['iteration_count']}")
    print(f"🤖 AI системы: {', '.join(status['ai_systems'])}")


if __name__ == "__main__":
    asyncio.run(main())
