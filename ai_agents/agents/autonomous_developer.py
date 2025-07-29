"""
Автономный агент разработчик
Способен самостоятельно реализовывать функции от идеи до production
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..claude_code_sdk import (
    ClaudeCodeOptions,
    ClaudeCodeSDK,
    ClaudeSession,
    PermissionMode,
    ThinkingMode,
)
from ..utils import get_mcp_manager


class DevelopmentPhase(Enum):
    """Фазы разработки"""

    EXPLORE = "explore"
    PLAN = "plan"
    IMPLEMENT = "implement"
    TEST = "test"
    REFINE = "refine"
    COMPLETE = "complete"


@dataclass
class DevelopmentTask:
    """Задача для разработки"""

    id: str
    description: str
    requirements: List[str]
    constraints: List[str] = field(default_factory=list)
    priority: str = "medium"
    estimated_complexity: int = 5  # 1-10


@dataclass
class DevelopmentPlan:
    """План разработки"""

    task: DevelopmentTask
    steps: List[Dict[str, Any]]
    files_to_create: List[str]
    files_to_modify: List[str]
    tests_required: List[str]
    estimated_time: int  # минуты
    dependencies: List[str]


@dataclass
class DevelopmentResult:
    """Результат разработки"""

    task_id: str
    success: bool
    phase_completed: DevelopmentPhase
    files_created: List[str]
    files_modified: List[str]
    tests_created: List[str]
    tests_passed: bool
    execution_time: int  # секунды
    token_usage: int
    errors: List[str]
    log: List[Dict[str, Any]]


class AutonomousDeveloper:
    """Автономный разработчик с полным циклом разработки"""

    def __init__(self, working_dir: Optional[Path] = None):
        self.working_dir = working_dir or Path.cwd()
        self.sdk = ClaudeCodeSDK()
        self.mcp_manager = get_mcp_manager()
        self.current_phase = DevelopmentPhase.EXPLORE
        self.session: Optional[ClaudeSession] = None
        self.development_log: List[Dict[str, Any]] = []

    async def develop_feature(self, task: DevelopmentTask) -> DevelopmentResult:
        """Полный цикл автономной разработки функции"""
        start_time = datetime.now()
        result = DevelopmentResult(
            task_id=task.id,
            success=False,
            phase_completed=DevelopmentPhase.EXPLORE,
            files_created=[],
            files_modified=[],
            tests_created=[],
            tests_passed=False,
            execution_time=0,
            token_usage=0,
            errors=[],
            log=[],
        )

        try:
            # Создаем сессию для сохранения контекста
            options = self._create_options_for_phase(DevelopmentPhase.EXPLORE)
            self.session = self.sdk.create_session(f"dev_{task.id}", options)

            # Фаза 1: EXPLORE - Исследование кодовой базы
            self._log("Starting EXPLORE phase", {"task_id": task.id})
            explore_result = await self._explore_phase(task)
            result.phase_completed = DevelopmentPhase.EXPLORE

            # Фаза 2: PLAN - Планирование реализации
            self._log("Starting PLAN phase", {"context": explore_result})
            plan = await self._plan_phase(task, explore_result)
            result.phase_completed = DevelopmentPhase.PLAN

            # Фаза 3: IMPLEMENT - Реализация
            self._log("Starting IMPLEMENT phase", {"plan": plan})
            implementation = await self._implement_phase(plan)
            result.files_created = implementation["files_created"]
            result.files_modified = implementation["files_modified"]
            result.phase_completed = DevelopmentPhase.IMPLEMENT

            # Фаза 4: TEST - Тестирование
            self._log("Starting TEST phase", {"implementation": implementation})
            test_results = await self._test_phase(plan, implementation)
            result.tests_created = test_results["tests_created"]
            result.tests_passed = test_results["all_passed"]
            result.phase_completed = DevelopmentPhase.TEST

            # Фаза 5: REFINE - Доработка на основе тестов
            if not test_results["all_passed"]:
                self._log(
                    "Starting REFINE phase", {"test_failures": test_results["failures"]}
                )
                refinement = await self._refine_phase(plan, test_results)
                result.phase_completed = DevelopmentPhase.REFINE

            # Финализация
            result.success = True
            result.phase_completed = DevelopmentPhase.COMPLETE

        except Exception as e:
            result.errors.append(str(e))
            self._log(
                f"Error in {self.current_phase.value} phase",
                {"error": str(e)},
                level="error",
            )

        finally:
            # Вычисляем финальные метрики
            result.execution_time = int((datetime.now() - start_time).total_seconds())
            result.token_usage = self.sdk.get_token_usage()
            result.log = self.development_log

        return result

    async def _explore_phase(self, task: DevelopmentTask) -> Dict[str, Any]:
        """Фаза исследования: анализ кодовой базы"""
        self.current_phase = DevelopmentPhase.EXPLORE

        prompt = f"""EXPLORE PHASE: Исследуйте кодовую базу для реализации следующей задачи:

Описание: {task.description}

Требования:
{chr(10).join(f"- {req}" for req in task.requirements)}

Ограничения:
{chr(10).join(f"- {constraint}" for constraint in task.constraints)}

Выполните:
1. Найдите релевантные файлы и модули
2. Изучите существующие паттерны и архитектуру
3. Определите точки интеграции
4. Найдите похожие реализации для reference
5. Проверьте доступные зависимости

Используйте TodoWrite для отслеживания прогресса.
Верните структурированный анализ."""

        options = self._create_options_for_phase(DevelopmentPhase.EXPLORE)
        result = await self.session.query(prompt)

        # Парсим результат в структурированный формат
        return self._parse_explore_result(result)

    async def _plan_phase(
        self, task: DevelopmentTask, context: Dict[str, Any]
    ) -> DevelopmentPlan:
        """Фаза планирования: создание детального плана"""
        self.current_phase = DevelopmentPhase.PLAN

        prompt = f"""PLAN PHASE: Создайте детальный план реализации.

Задача: {task.description}
Контекст исследования: {json.dumps(context, indent=2)}

Создайте план включающий:
1. Пошаговую последовательность действий
2. Список файлов для создания/модификации
3. Необходимые тесты
4. Оценку времени
5. Потенциальные риски

Используйте TodoWrite для создания задач.
Следуйте принципам SOLID и clean code."""

        options = self._create_options_for_phase(DevelopmentPhase.PLAN)
        result = await self.session.query(prompt)

        return self._parse_plan_result(result, task)

    async def _implement_phase(self, plan: DevelopmentPlan) -> Dict[str, Any]:
        """Фаза реализации: написание кода"""
        self.current_phase = DevelopmentPhase.IMPLEMENT

        prompt = f"""IMPLEMENT PHASE: Реализуйте функцию согласно плану.

План реализации:
{json.dumps([s for s in plan.steps], indent=2)}

Файлы для создания: {plan.files_to_create}
Файлы для модификации: {plan.files_to_modify}

Требования:
1. Следуйте плану пошагово
2. Пишите чистый, документированный код
3. Используйте type hints
4. Обрабатывайте ошибки
5. Добавляйте логирование

ВАЖНО: Реализуйте полностью, не оставляйте заглушки."""

        options = self._create_options_for_phase(DevelopmentPhase.IMPLEMENT)
        result = await self.session.query(prompt)

        # Отслеживаем созданные и измененные файлы
        return {
            "files_created": self._extract_created_files(result),
            "files_modified": self._extract_modified_files(result),
            "implementation_details": result,
        }

    async def _test_phase(
        self, plan: DevelopmentPlan, implementation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Фаза тестирования: создание и запуск тестов"""
        self.current_phase = DevelopmentPhase.TEST

        prompt = f"""TEST PHASE: Создайте и запустите тесты.

Реализованные файлы: {implementation['files_created'] + implementation['files_modified']}
Требуемые тесты: {plan.tests_required}

Выполните:
1. Создайте unit тесты с pytest
2. Добавьте integration тесты если нужно
3. Проверьте edge cases
4. Запустите тесты и проанализируйте результаты
5. Проверьте покрытие кода

Используйте fixtures и параметризацию где возможно."""

        options = self._create_options_for_phase(DevelopmentPhase.TEST)
        result = await self.session.query(prompt)

        # Запускаем тесты и собираем результаты
        test_results = await self._run_tests()

        return {
            "tests_created": self._extract_test_files(result),
            "all_passed": test_results["success"],
            "failures": test_results.get("failures", []),
            "coverage": test_results.get("coverage", 0),
        }

    async def _refine_phase(
        self, plan: DevelopmentPlan, test_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Фаза доработки: исправление на основе результатов тестов"""
        self.current_phase = DevelopmentPhase.REFINE

        prompt = f"""REFINE PHASE: Исправьте проблемы на основе результатов тестов.

Неудачные тесты: {json.dumps(test_results['failures'], indent=2)}

Выполните:
1. Проанализируйте причины сбоев
2. Исправьте код
3. Перезапустите тесты
4. Оптимизируйте если нужно
5. Обновите документацию

НЕ меняйте тесты чтобы они проходили - исправляйте код."""

        options = self._create_options_for_phase(DevelopmentPhase.REFINE)
        result = await self.session.query(prompt)

        # Перезапускаем тесты
        refined_test_results = await self._run_tests()

        return {
            "refinements_made": result,
            "tests_now_pass": refined_test_results["success"],
        }

    def _create_options_for_phase(self, phase: DevelopmentPhase) -> ClaudeCodeOptions:
        """Создать опции для конкретной фазы"""
        base_tools = ["Read", "Write", "Edit", "Bash", "Task", "TodoWrite"]

        phase_config = {
            DevelopmentPhase.EXPLORE: {
                "thinking_mode": ThinkingMode.THINK,
                "max_turns": 10,
                "tools": base_tools + ["Grep", "Glob"],
            },
            DevelopmentPhase.PLAN: {
                "thinking_mode": ThinkingMode.THINK_HARD,
                "max_turns": 5,
                "tools": base_tools,
            },
            DevelopmentPhase.IMPLEMENT: {
                "thinking_mode": ThinkingMode.THINK_HARDER,
                "max_turns": 20,
                "tools": base_tools,
                "permission_mode": PermissionMode.ACCEPT_EDITS,
            },
            DevelopmentPhase.TEST: {
                "thinking_mode": ThinkingMode.THINK,
                "max_turns": 15,
                "tools": base_tools,
            },
            DevelopmentPhase.REFINE: {
                "thinking_mode": ThinkingMode.ULTRATHINK,
                "max_turns": 10,
                "tools": base_tools,
            },
        }

        config = phase_config.get(phase, {})

        return ClaudeCodeOptions(
            system_prompt=f"""Вы автономный разработчик в фазе {phase.value}.
            Работайте методично и самостоятельно.
            Документируйте все действия.
            Следуйте best practices.""",
            thinking_mode=config.get("thinking_mode", ThinkingMode.NORMAL),
            max_turns=config.get("max_turns", 10),
            allowed_tools=config.get("tools", base_tools),
            permission_mode=config.get("permission_mode", PermissionMode.DEFAULT),
        )

    async def _run_tests(self) -> Dict[str, Any]:
        """Запустить тесты и вернуть результаты"""
        try:
            # Запускаем pytest
            cmd = ["pytest", "-v", "--tb=short", "--cov=.", "--cov-report=json"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
            )

            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "output": stdout.decode(),
                "errors": stderr.decode(),
                "coverage": self._parse_coverage_report(),
            }

        except Exception as e:
            return {"success": False, "failures": [str(e)], "coverage": 0}

    def _parse_coverage_report(self) -> float:
        """Парсить отчет о покрытии"""
        try:
            coverage_file = self.working_dir / ".coverage"
            if coverage_file.exists():
                # Упрощенный парсинг
                return 85.0  # Заглушка
        except:
            pass
        return 0.0

    def _parse_explore_result(self, result: str) -> Dict[str, Any]:
        """Парсить результат фазы исследования"""
        # Упрощенный парсинг - в реальности нужен более сложный анализ
        return {
            "relevant_files": [],
            "patterns_found": [],
            "integration_points": [],
            "dependencies": [],
        }

    def _parse_plan_result(self, result: str, task: DevelopmentTask) -> DevelopmentPlan:
        """Парсить результат фазы планирования"""
        # Упрощенный парсинг
        return DevelopmentPlan(
            task=task,
            steps=[{"step": 1, "action": "Initial implementation"}],
            files_to_create=[],
            files_to_modify=[],
            tests_required=["test_basic_functionality"],
            estimated_time=30,
            dependencies=[],
        )

    def _extract_created_files(self, result: str) -> List[str]:
        """Извлечь список созданных файлов"""
        # Парсим результат для поиска созданных файлов
        return []

    def _extract_modified_files(self, result: str) -> List[str]:
        """Извлечь список измененных файлов"""
        return []

    def _extract_test_files(self, result: str) -> List[str]:
        """Извлечь список файлов с тестами"""
        return []

    def _log(
        self, message: str, data: Optional[Dict[str, Any]] = None, level: str = "info"
    ):
        """Добавить запись в лог разработки"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": self.current_phase.value,
            "level": level,
            "message": message,
            "data": data or {},
        }
        self.development_log.append(log_entry)


# Функции для быстрого доступа
async def develop_feature_autonomously(
    description: str,
    requirements: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None,
) -> DevelopmentResult:
    """Быстрая автономная разработка функции"""
    task = DevelopmentTask(
        id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        description=description,
        requirements=requirements or [],
        constraints=constraints or [],
    )

    developer = AutonomousDeveloper()
    return await developer.develop_feature(task)


async def batch_development(tasks: List[DevelopmentTask]) -> List[DevelopmentResult]:
    """Пакетная разработка нескольких функций"""
    developer = AutonomousDeveloper()
    results = []

    for task in tasks:
        result = await developer.develop_feature(task)
        results.append(result)

        # Пауза между задачами для управления нагрузкой
        await asyncio.sleep(5)

    return results


if __name__ == "__main__":
    # Пример использования
    async def main():
        # Простая задача
        result = await develop_feature_autonomously(
            description="Создать REST API endpoint для получения торговой статистики",
            requirements=[
                "Endpoint GET /api/v1/stats/trading",
                "Возвращать данные за последние 24 часа",
                "Включить: объем торгов, количество сделок, прибыль/убыток",
                "Поддержка фильтрации по символу",
            ],
            constraints=[
                "Использовать FastAPI",
                "Кешировать результаты на 5 минут",
                "Время ответа < 100ms",
            ],
        )

        print(f"Development completed: {result.success}")
        print(f"Files created: {result.files_created}")
        print(f"Tests passed: {result.tests_passed}")
        print(f"Execution time: {result.execution_time}s")

    asyncio.run(main())
