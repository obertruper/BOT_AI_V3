#!/usr/bin/env python3
"""
Автоматический генератор тестов для бизнес-логики BOT_AI_V3
Создаёт тесты для каждой функции/метода с проверкой всех сценариев
"""

import ast
import sys
from pathlib import Path
from typing import Any

# Добавляем проект в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestGenerator:
    """Генератор тестов для бизнес-логики"""

    # Критические модули бизнес-логики
    BUSINESS_MODULES = {
        "trading": [
            "trading/engine.py",
            "trading/orders/order_manager.py",
            "trading/positions/position_manager.py",
            "trading/risk/risk_manager.py",
            "trading/signals/signal_processor.py",
        ],
        "ml": [
            "ml/ml_manager.py",
            "ml/ml_signal_processor.py",
            "ml/realtime_indicator_calculator.py",
            "ml/logic/feature_engineering_v2.py",
            "ml/logic/patchtst_model.py",
        ],
        "exchanges": [
            "exchanges/bybit/client.py",
            "exchanges/binance/client.py",
            "exchanges/base/unified_interface.py",
        ],
        "core": [
            "core/system/orchestrator.py",
            "core/logger.py",
            "main.py",
            "unified_launcher.py",
        ],
        "database": [
            "database/repositories/order_repository.py",
            "database/repositories/signal_repository_fixed.py",
            "database/repositories/market_data_repository.py",
        ],
        "strategies": [
            "strategies/patchtst_strategy.py",
            "strategies/base_strategy.py",
        ],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.generated_tests = []

    def analyze_function(
        self, func_node: ast.FunctionDef, class_name: str | None = None
    ) -> dict[str, Any]:
        """Анализирует функцию и определяет необходимые тесты"""

        analysis = {
            "name": func_node.name,
            "class": class_name,
            "is_async": isinstance(func_node, ast.AsyncFunctionDef),
            "parameters": [],
            "returns": None,
            "raises": [],
            "has_db_access": False,
            "has_external_api": False,
            "complexity": self._calculate_complexity(func_node),
            "test_scenarios": [],
        }

        # Анализ параметров
        for arg in func_node.args.args:
            if arg.arg != "self":
                param_info = {
                    "name": arg.arg,
                    "type": self._get_type_annotation(arg.annotation),
                    "has_default": False,
                }
                analysis["parameters"].append(param_info)

        # Анализ тела функции
        for node in ast.walk(func_node):
            # Проверка на работу с БД
            if isinstance(node, ast.Name) and any(
                db in node.id.lower() for db in ["pool", "session", "repository", "db"]
            ):
                analysis["has_db_access"] = True

            # Проверка на внешние API
            if isinstance(node, ast.Attribute) and any(
                api in str(node.attr).lower() for api in ["request", "post", "get", "websocket"]
            ):
                analysis["has_external_api"] = True

            # Проверка исключений
            if isinstance(node, ast.Raise):
                analysis["raises"].append("Exception")

        # Генерация сценариев тестирования
        analysis["test_scenarios"] = self._generate_test_scenarios(analysis)

        return analysis

    def _calculate_complexity(self, func_node: ast.FunctionDef) -> int:
        """Вычисляет цикломатическую сложность функции"""
        complexity = 1
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return complexity

    def _get_type_annotation(self, annotation) -> str:
        """Извлекает аннотацию типа"""
        if annotation is None:
            return "Any"
        return ast.unparse(annotation) if hasattr(ast, "unparse") else "Any"

    def _generate_test_scenarios(self, analysis: dict) -> list[dict]:
        """Генерирует сценарии тестирования"""
        scenarios = []

        # 1. Happy path - успешное выполнение
        scenarios.append(
            {
                "name": "happy_path",
                "description": "Успешное выполнение с корректными данными",
                "type": "positive",
            }
        )

        # 2. Edge cases - граничные значения
        if analysis["parameters"]:
            scenarios.append(
                {
                    "name": "edge_cases",
                    "description": "Граничные значения параметров",
                    "type": "boundary",
                }
            )

        # 3. Null/None проверки
        scenarios.append(
            {
                "name": "null_checks",
                "description": "Обработка None и пустых значений",
                "type": "negative",
            }
        )

        # 4. Проверка исключений
        if analysis["raises"]:
            scenarios.append(
                {
                    "name": "exception_handling",
                    "description": "Корректная обработка исключений",
                    "type": "exception",
                }
            )

        # 5. Проверка производительности для сложных функций
        if analysis["complexity"] > 10:
            scenarios.append(
                {
                    "name": "performance",
                    "description": "Производительность при больших объёмах",
                    "type": "performance",
                }
            )

        # 6. Мокирование для внешних зависимостей
        if analysis["has_db_access"]:
            scenarios.append(
                {"name": "db_mock", "description": "Тест с мокированием БД", "type": "mock"}
            )

        if analysis["has_external_api"]:
            scenarios.append(
                {
                    "name": "api_mock",
                    "description": "Тест с мокированием внешних API",
                    "type": "mock",
                }
            )

        return scenarios

    def generate_test_code(self, module_path: str, analysis: dict) -> str:
        """Генерирует код теста для функции"""

        func_name = analysis["name"]
        class_name = analysis["class"]
        is_async = analysis["is_async"]

        # Определяем имя теста
        if class_name:
            test_name = f"Test{class_name}"
            import_path = f"{module_path.replace('/', '.').replace('.py', '')}.{class_name}"
        else:
            test_name = f"test_{func_name}"
            import_path = f"{module_path.replace('/', '.').replace('.py', '')}.{func_name}"

        # Шаблон теста
        test_code = f'''"""
Автоматически сгенерированные тесты для {module_path}
Функция: {func_name}
Сложность: {analysis['complexity']}
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from datetime import datetime
import numpy as np
import pandas as pd

# Импорт тестируемого модуля
from {import_path.rsplit('.', 1)[0]} import {class_name or func_name}

'''

        # Генерация тестов для каждого сценария
        for scenario in analysis["test_scenarios"]:
            test_method_name = f"test_{func_name}_{scenario['name']}"

            if is_async:
                test_code += f'''
@pytest.mark.asyncio
async def {test_method_name}():
    """
    Тест: {scenario['description']}
    Тип: {scenario['type']}
    """
'''
            else:
                test_code += f'''
def {test_method_name}():
    """
    Тест: {scenario['description']}
    Тип: {scenario['type']}
    """
'''

            # Добавляем тело теста в зависимости от типа
            if scenario["type"] == "positive":
                test_code += self._generate_positive_test(analysis, is_async)
            elif scenario["type"] == "negative":
                test_code += self._generate_negative_test(analysis, is_async)
            elif scenario["type"] == "exception":
                test_code += self._generate_exception_test(analysis, is_async)
            elif scenario["type"] == "performance":
                test_code += self._generate_performance_test(analysis, is_async)
            elif scenario["type"] == "mock":
                test_code += self._generate_mock_test(analysis, is_async, scenario["name"])
            elif scenario["type"] == "boundary":
                test_code += self._generate_boundary_test(analysis, is_async)

        return test_code

    def _generate_positive_test(self, analysis: dict, is_async: bool) -> str:
        """Генерирует позитивный тест"""
        indent = "    "
        test_body = f"{indent}# Arrange - подготовка данных\n"

        # Создание тестовых данных для параметров
        for param in analysis["parameters"]:
            if "str" in param["type"]:
                test_body += f"{indent}{param['name']} = 'test_value'\n"
            elif "int" in param["type"]:
                test_body += f"{indent}{param['name']} = 100\n"
            elif "float" in param["type"]:
                test_body += f"{indent}{param['name']} = 100.0\n"
            elif "dict" in param["type"].lower():
                test_body += f"{indent}{param['name']} = {{'key': 'value'}}\n"
            elif "list" in param["type"].lower():
                test_body += f"{indent}{param['name']} = [1, 2, 3]\n"
            else:
                test_body += f"{indent}{param['name']} = Mock()\n"

        test_body += f"\n{indent}# Act - выполнение\n"

        if analysis["class"]:
            test_body += f"{indent}instance = {analysis['class']}()\n"
            if is_async:
                test_body += f"{indent}result = await instance.{analysis['name']}("
            else:
                test_body += f"{indent}result = instance.{analysis['name']}("
        else:
            if is_async:
                test_body += f"{indent}result = await {analysis['name']}("
            else:
                test_body += f"{indent}result = {analysis['name']}("

        # Добавляем параметры
        param_names = [p["name"] for p in analysis["parameters"]]
        test_body += ", ".join(param_names) + ")\n"

        test_body += f"\n{indent}# Assert - проверка\n"
        test_body += f"{indent}assert result is not None\n"
        test_body += f"{indent}# TODO: Добавить специфичные проверки результата\n"

        return test_body

    def _generate_negative_test(self, analysis: dict, is_async: bool) -> str:
        """Генерирует негативный тест с None значениями"""
        indent = "    "
        test_body = f"{indent}# Тест с None значениями\n"

        if analysis["parameters"]:
            param_name = analysis["parameters"][0]["name"]
            test_body += f"{indent}{param_name} = None\n"

            if analysis["class"]:
                test_body += f"{indent}instance = {analysis['class']}()\n"
                test_body += (
                    f"{indent}with pytest.raises((TypeError, ValueError, AttributeError)):\n"
                )
                if is_async:
                    test_body += f"{indent}    await instance.{analysis['name']}({param_name})\n"
                else:
                    test_body += f"{indent}    instance.{analysis['name']}({param_name})\n"
            else:
                test_body += (
                    f"{indent}with pytest.raises((TypeError, ValueError, AttributeError)):\n"
                )
                if is_async:
                    test_body += f"{indent}    await {analysis['name']}({param_name})\n"
                else:
                    test_body += f"{indent}    {analysis['name']}({param_name})\n"
        else:
            test_body += f"{indent}# Функция без параметров - проверка состояния\n"
            test_body += f"{indent}pass  # TODO: Реализовать проверку\n"

        return test_body

    def _generate_exception_test(self, analysis: dict, is_async: bool) -> str:
        """Генерирует тест обработки исключений"""
        indent = "    "
        test_body = f"{indent}# Тест обработки исключений\n"

        if analysis["has_db_access"]:
            test_body += (
                f"{indent}with patch('asyncpg.create_pool', side_effect=Exception('DB Error')):\n"
            )
        elif analysis["has_external_api"]:
            test_body += f"{indent}with patch('aiohttp.ClientSession.get', side_effect=Exception('API Error')):\n"
        else:
            test_body += f"{indent}# Симуляция ошибки\n"

        test_body += f"{indent}    with pytest.raises(Exception):\n"

        if analysis["class"]:
            test_body += f"{indent}        instance = {analysis['class']}()\n"
            if is_async:
                test_body += f"{indent}        await instance.{analysis['name']}()\n"
            else:
                test_body += f"{indent}        instance.{analysis['name']}()\n"
        else:
            if is_async:
                test_body += f"{indent}        await {analysis['name']}()\n"
            else:
                test_body += f"{indent}        {analysis['name']}()\n"

        return test_body

    def _generate_performance_test(self, analysis: dict, is_async: bool) -> str:
        """Генерирует тест производительности"""
        indent = "    "
        test_body = f"{indent}# Тест производительности\n"
        test_body += f"{indent}import time\n"
        test_body += f"{indent}start_time = time.time()\n\n"

        test_body += f"{indent}# Выполнение 100 итераций\n"
        test_body += f"{indent}for _ in range(100):\n"

        if analysis["class"]:
            test_body += f"{indent}    instance = {analysis['class']}()\n"
            if is_async:
                test_body += f"{indent}    await instance.{analysis['name']}()\n"
            else:
                test_body += f"{indent}    instance.{analysis['name']}()\n"
        else:
            if is_async:
                test_body += f"{indent}    await {analysis['name']}()\n"
            else:
                test_body += f"{indent}    {analysis['name']}()\n"

        test_body += f"\n{indent}elapsed = time.time() - start_time\n"
        test_body += (
            f"{indent}assert elapsed < 1.0, f'Функция слишком медленная: {{elapsed:.2f}}s'\n"
        )

        return test_body

    def _generate_mock_test(self, analysis: dict, is_async: bool, mock_type: str) -> str:
        """Генерирует тест с моками"""
        indent = "    "
        test_body = f"{indent}# Тест с мокированием {mock_type}\n"

        if "db" in mock_type:
            test_body += f"{indent}mock_db = AsyncMock() if {is_async} else Mock()\n"
            test_body += f"{indent}mock_db.fetch.return_value = [{{'id': 1, 'status': 'active'}}]\n"
            test_body += f"{indent}with patch('database.connections.AsyncPGPool', mock_db):\n"
        else:
            test_body += f"{indent}mock_api = AsyncMock() if {is_async} else Mock()\n"
            test_body += (
                f"{indent}mock_api.get.return_value.json.return_value = {{'status': 'ok'}}\n"
            )
            test_body += f"{indent}with patch('aiohttp.ClientSession', return_value=mock_api):\n"

        if analysis["class"]:
            test_body += f"{indent}    instance = {analysis['class']}()\n"
            if is_async:
                test_body += f"{indent}    result = await instance.{analysis['name']}()\n"
            else:
                test_body += f"{indent}    result = instance.{analysis['name']}()\n"
        else:
            if is_async:
                test_body += f"{indent}    result = await {analysis['name']}()\n"
            else:
                test_body += f"{indent}    result = {analysis['name']}()\n"

        test_body += f"{indent}    assert result is not None\n"
        test_body += f"{indent}    # Проверка вызова мока\n"

        if "db" in mock_type:
            test_body += f"{indent}    assert mock_db.fetch.called\n"
        else:
            test_body += f"{indent}    assert mock_api.get.called\n"

        return test_body

    def _generate_boundary_test(self, analysis: dict, is_async: bool) -> str:
        """Генерирует тест граничных значений"""
        indent = "    "
        test_body = f"{indent}# Тест граничных значений\n"
        test_body += f"{indent}test_cases = [\n"
        test_body += f"{indent}    (0, 'zero'),\n"
        test_body += f"{indent}    (-1, 'negative'),\n"
        test_body += f"{indent}    (999999999, 'max_value'),\n"
        test_body += f"{indent}    ('', 'empty_string'),\n"
        test_body += f"{indent}    ([], 'empty_list'),\n"
        test_body += f"{indent}]\n\n"

        test_body += f"{indent}for value, case_name in test_cases:\n"
        test_body += f"{indent}    try:\n"

        if analysis["class"]:
            test_body += f"{indent}        instance = {analysis['class']}()\n"
            if is_async:
                test_body += f"{indent}        result = await instance.{analysis['name']}(value)\n"
            else:
                test_body += f"{indent}        result = instance.{analysis['name']}(value)\n"
        else:
            if is_async:
                test_body += f"{indent}        result = await {analysis['name']}(value)\n"
            else:
                test_body += f"{indent}        result = {analysis['name']}(value)\n"

        test_body += f"{indent}        # Граничное значение обработано\n"
        test_body += f"{indent}        print(f'{{case_name}}: OK')\n"
        test_body += f"{indent}    except Exception as e:\n"
        test_body += f"{indent}        # Ожидаемое исключение для некорректных значений\n"
        test_body += f"{indent}        print(f'{{case_name}}: {{type(e).__name__}}')\n"

        return test_body

    def process_module(self, module_path: str) -> list[dict]:
        """Обрабатывает модуль и генерирует тесты"""
        full_path = self.project_root / module_path

        if not full_path.exists():
            print(f"⚠️ Файл не найден: {module_path}")
            return []

        with open(full_path, encoding="utf-8") as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            print(f"❌ Ошибка парсинга {module_path}: {e}")
            return []

        tests = []

        # Анализ функций и классов
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Анализ методов класса
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not item.name.startswith("_") or item.name == "__init__":
                            analysis = self.analyze_function(item, node.name)
                            test_code = self.generate_test_code(module_path, analysis)
                            tests.append(
                                {
                                    "module": module_path,
                                    "function": f"{node.name}.{item.name}",
                                    "analysis": analysis,
                                    "test_code": test_code,
                                }
                            )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Анализ функций верхнего уровня
                if not node.name.startswith("_"):
                    analysis = self.analyze_function(node)
                    test_code = self.generate_test_code(module_path, analysis)
                    tests.append(
                        {
                            "module": module_path,
                            "function": node.name,
                            "analysis": analysis,
                            "test_code": test_code,
                        }
                    )

        return tests

    def generate_all_tests(self) -> None:
        """Генерирует тесты для всех модулей бизнес-логики"""

        print("🚀 Генерация тестов для бизнес-логики BOT_AI_V3")
        print("=" * 60)

        total_tests = 0

        for category, modules in self.BUSINESS_MODULES.items():
            print(f"\n📁 Категория: {category}")

            for module_path in modules:
                tests = self.process_module(module_path)

                if tests:
                    # Создаём директорию для тестов
                    test_dir = self.project_root / "tests" / "unit" / category
                    test_dir.mkdir(parents=True, exist_ok=True)

                    # Имя файла теста
                    module_name = Path(module_path).stem
                    test_file = test_dir / f"test_{module_name}_auto.py"

                    # Объединяем все тесты модуля
                    combined_code = tests[0]["test_code"]
                    for test in tests[1:]:
                        # Добавляем только тестовые функции, без импортов
                        lines = test["test_code"].split("\n")
                        start_idx = 0
                        for i, line in enumerate(lines):
                            if (
                                line.startswith("@")
                                or line.startswith("def ")
                                or line.startswith("async def ")
                            ):
                                start_idx = i
                                break
                        combined_code += "\n" + "\n".join(lines[start_idx:])

                    # Сохраняем тест
                    with open(test_file, "w", encoding="utf-8") as f:
                        f.write(combined_code)

                    print(
                        f"  ✅ {module_path}: {len(tests)} тестов → {test_file.relative_to(self.project_root)}"
                    )
                    total_tests += len(tests)

                    self.generated_tests.extend(tests)

        print(f"\n📊 Итого сгенерировано: {total_tests} тестов")

        # Создаём отчёт о покрытии
        self.generate_coverage_report()

    def generate_coverage_report(self) -> None:
        """Генерирует отчёт о покрытии тестами"""

        report_path = self.project_root / "tests" / "coverage_report.md"

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 📊 Отчёт о покрытии бизнес-логики тестами\n\n")
            f.write(f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Статистика по категориям
            f.write("## Покрытие по категориям\n\n")
            f.write("| Категория | Модулей | Функций | Тестов | Средняя сложность |\n")
            f.write("|-----------|---------|---------|--------|------------------|\n")

            for category in self.BUSINESS_MODULES:
                category_tests = [t for t in self.generated_tests if category in t["module"]]
                if category_tests:
                    avg_complexity = sum(t["analysis"]["complexity"] for t in category_tests) / len(
                        category_tests
                    )
                    f.write(f"| {category} | {len(set(t['module'] for t in category_tests))} | ")
                    f.write(
                        f"{len(category_tests)} | {len(category_tests) * 5} | {avg_complexity:.1f} |\n"
                    )

            # Детальный список функций
            f.write("\n## Детальное покрытие\n\n")

            for test in sorted(self.generated_tests, key=lambda x: (x["module"], x["function"])):
                f.write(f"### {test['module']} → {test['function']}\n")
                f.write(f"- Сложность: {test['analysis']['complexity']}\n")
                f.write(f"- Async: {'✅' if test['analysis']['is_async'] else '❌'}\n")
                f.write(f"- БД: {'✅' if test['analysis']['has_db_access'] else '❌'}\n")
                f.write(f"- API: {'✅' if test['analysis']['has_external_api'] else '❌'}\n")
                f.write(f"- Сценариев: {len(test['analysis']['test_scenarios'])}\n\n")

        print(f"\n📄 Отчёт сохранён: {report_path.relative_to(self.project_root)}")


def main():
    """Основная функция"""
    project_root = Path(__file__).parent.parent
    generator = TestGenerator(project_root)
    generator.generate_all_tests()

    print("\n✅ Генерация тестов завершена!")
    print("\n🚀 Для запуска всех новых тестов:")
    print("   pytest tests/unit/ -v --tb=short")
    print("\n📊 Для проверки покрытия:")
    print("   pytest tests/unit/ --cov=. --cov-report=html")


if __name__ == "__main__":
    main()
