#!/usr/bin/env python3
"""
Безопасное удаление неиспользуемого кода в BOT_AI_V3
Анализирует и предлагает удаление dead code
"""

import ast
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class RemovalCandidate:
    """Кандидат на удаление"""

    function_name: str
    file_path: str
    line_start: int
    line_end: int
    risk_level: str  # LOW, MEDIUM, HIGH
    reason: str
    impact_assessment: str
    safe_to_remove: bool
    backup_created: bool = False


@dataclass
class RemovalPlan:
    """План удаления неиспользуемого кода"""

    candidates: list[RemovalCandidate]
    total_lines_to_remove: int
    estimated_size_reduction: str
    affected_files: list[str]
    backup_directory: str
    safety_checks_passed: bool


class CodeRemovalSafetyChecker:
    """Проверка безопасности удаления кода"""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def check_removal_safety(self, candidate: RemovalCandidate) -> dict[str, Any]:
        """Проверяет безопасность удаления функции"""
        checks = {
            "import_references": self._check_import_references(candidate),
            "dynamic_calls": self._check_dynamic_calls(candidate),
            "string_references": self._check_string_references(candidate),
            "decorator_usage": self._check_decorator_usage(candidate),
            "inheritance_chain": self._check_inheritance_chain(candidate),
            "test_dependencies": self._check_test_dependencies(candidate),
            "api_endpoints": self._check_api_endpoints(candidate),
            "configuration_files": self._check_configuration_files(candidate),
        }

        # Оценка общей безопасности
        safety_score = sum(1 for check in checks.values() if check["safe"])
        total_checks = len(checks)
        safety_percentage = (safety_score / total_checks) * 100

        return {
            "checks": checks,
            "safety_score": safety_score,
            "total_checks": total_checks,
            "safety_percentage": safety_percentage,
            "safe_to_remove": safety_percentage >= 80,  # 80% порог безопасности
            "warnings": [check["warning"] for check in checks.values() if check.get("warning")],
        }

    def _check_import_references(self, candidate: RemovalCandidate) -> dict[str, Any]:
        """Проверяет есть ли импорты этой функции"""
        function_name = candidate.function_name
        found_references = []

        # Ищем по всем Python файлам
        for py_file in self.project_root.rglob("*.py"):
            if py_file.name == Path(candidate.file_path).name:
                continue  # Пропускаем сам файл

            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Ищем импорты
                if (
                    f"import {function_name}" in content
                    or f"from .* import.*{function_name}" in content
                ):
                    found_references.append(str(py_file.relative_to(self.project_root)))

            except Exception:
                continue

        return {
            "safe": len(found_references) == 0,
            "references": found_references,
            "warning": (
                f"Найдены импорты в {len(found_references)} файлах" if found_references else None
            ),
        }

    def _check_dynamic_calls(self, candidate: RemovalCandidate) -> dict[str, Any]:
        """Проверяет динамические вызовы (getattr, exec, eval)"""
        function_name = candidate.function_name
        dynamic_patterns = [
            f"getattr.*{function_name}",
            f"hasattr.*{function_name}",
            f"exec.*{function_name}",
            f"eval.*{function_name}",
            f'"{function_name}"',
            f"'{function_name}'",
        ]

        found_references = []

        for py_file in self.project_root.rglob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                for pattern in dynamic_patterns:
                    if pattern in content:
                        found_references.append(
                            {
                                "file": str(py_file.relative_to(self.project_root)),
                                "pattern": pattern,
                            }
                        )

            except Exception:
                continue

        return {
            "safe": len(found_references) == 0,
            "references": found_references,
            "warning": (
                f"Найдены динамические ссылки в {len(found_references)} местах"
                if found_references
                else None
            ),
        }

    def _check_string_references(self, candidate: RemovalCandidate) -> dict[str, Any]:
        """Проверяет строковые ссылки на функцию"""
        function_name = candidate.function_name
        found_references = []

        # Проверяем конфигурационные файлы
        config_extensions = [".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"]

        for ext in config_extensions:
            for config_file in self.project_root.rglob(f"*{ext}"):
                try:
                    with open(config_file, encoding="utf-8") as f:
                        content = f.read()

                    if function_name in content:
                        found_references.append(str(config_file.relative_to(self.project_root)))

                except Exception:
                    continue

        return {
            "safe": len(found_references) == 0,
            "references": found_references,
            "warning": (
                f"Найдены ссылки в конфигурациях: {found_references}" if found_references else None
            ),
        }

    def _check_decorator_usage(self, candidate: RemovalCandidate) -> dict[str, Any]:
        """Проверяет использование как декоратор"""
        function_name = candidate.function_name

        try:
            file_path = self.project_root / candidate.file_path
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            # Ищем использование как декоратор
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == function_name:
                            return {
                                "safe": False,
                                "usage": f"Используется как декоратор для {node.name}",
                                "warning": "Функция используется как декоратор",
                            }

            return {"safe": True}

        except Exception as e:
            return {"safe": False, "warning": f"Ошибка анализа декораторов: {e}"}

    def _check_inheritance_chain(self, candidate: RemovalCandidate) -> dict[str, Any]:
        """Проверяет цепочку наследования"""
        # Упрощённая проверка - можно расширить
        function_name = candidate.function_name

        # Проверяем является ли методом класса
        if "." in function_name or (
            function_name.startswith("__") and function_name.endswith("__")
        ):
            return {"safe": False, "warning": "Возможно метод класса или magic method"}

        return {"safe": True}

    def _check_test_dependencies(self, candidate: RemovalCandidate) -> dict[str, Any]:
        """Проверяет зависимости в тестах"""
        function_name = candidate.function_name
        found_in_tests = []

        test_dirs = [self.project_root / "tests", self.project_root / "test"]

        for test_dir in test_dirs:
            if test_dir.exists():
                for test_file in test_dir.rglob("*.py"):
                    try:
                        with open(test_file, encoding="utf-8") as f:
                            content = f.read()

                        if function_name in content:
                            found_in_tests.append(str(test_file.relative_to(self.project_root)))

                    except Exception:
                        continue

        return {
            "safe": len(found_in_tests) == 0,
            "references": found_in_tests,
            "warning": f"Используется в тестах: {found_in_tests}" if found_in_tests else None,
        }

    def _check_api_endpoints(self, candidate: RemovalCandidate) -> dict[str, Any]:
        """Проверяет API endpoints"""
        function_name = candidate.function_name

        # Ключевые слова API
        api_keywords = ["@app.", "@router.", "@api.", "route", "endpoint", "fastapi", "flask"]

        try:
            file_path = self.project_root / candidate.file_path
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Проверяем есть ли API декораторы рядом с функцией
            lines = content.split("\n")
            func_line = candidate.line_start - 1

            # Проверяем 5 строк до функции
            for i in range(max(0, func_line - 5), func_line):
                line = lines[i].strip()
                if any(keyword in line.lower() for keyword in api_keywords):
                    return {"safe": False, "warning": f"Возможно API endpoint: {line}"}

            return {"safe": True}

        except Exception:
            return {"safe": True}

    def _check_configuration_files(self, candidate: RemovalCandidate) -> dict[str, Any]:
        """Проверяет упоминания в конфигурационных файлах"""
        function_name = candidate.function_name
        found_configs = []

        # Специфичные для проекта конфигурации
        config_files = [
            "config/trading.yaml",
            "config/system.yaml",
            "config/ml/ml_config.yaml",
            ".env.example",
            "alembic.ini",
            "pytest.ini",
        ]

        for config_file in config_files:
            config_path = self.project_root / config_file
            if config_path.exists():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        content = f.read()

                    if function_name in content:
                        found_configs.append(config_file)

                except Exception:
                    continue

        return {
            "safe": len(found_configs) == 0,
            "references": found_configs,
            "warning": f"Упоминается в конфигурациях: {found_configs}" if found_configs else None,
        }


class UnusedCodeRemover:
    """Основной класс для удаления неиспользуемого кода"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.safety_checker = CodeRemovalSafetyChecker(project_root)
        self.backup_dir = None

    def analyze_removal_candidates(self, analysis_file: Path) -> list[RemovalCandidate]:
        """Анализирует кандидатов на удаление из файла анализа"""
        candidates = []

        try:
            with open(analysis_file, encoding="utf-8") as f:
                analysis_data = json.load(f)

            unused_functions = analysis_data.get("unused_code_candidates", [])

            for func_key in unused_functions:
                # Парсим func_key (format: "file.py:function_name")
                if ":" in func_key:
                    file_path, function_name = func_key.split(":", 1)

                    # Получаем информацию о функции
                    func_info = self._get_function_info(file_path, function_name)
                    if func_info:
                        candidate = RemovalCandidate(
                            function_name=function_name,
                            file_path=file_path,
                            line_start=func_info["line_start"],
                            line_end=func_info["line_end"],
                            risk_level=func_info["risk_level"],
                            reason=func_info["reason"],
                            impact_assessment="",
                            safe_to_remove=False,
                        )
                        candidates.append(candidate)

        except Exception as e:
            print(f"❌ Ошибка анализа файла {analysis_file}: {e}")

        return candidates

    def _get_function_info(self, file_path: str, function_name: str) -> dict[str, Any] | None:
        """Получает информацию о функции из файла"""
        try:
            full_path = self.project_root / file_path
            with open(full_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            lines = content.split("\n")

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == function_name:
                        # Найдём конец функции
                        line_end = node.lineno
                        for child in ast.walk(node):
                            if hasattr(child, "lineno") and child.lineno > line_end:
                                line_end = child.lineno

                        # Если не нашли конец, ищем следующую функцию или конец файла
                        if line_end == node.lineno:
                            line_end = len(lines)
                            for next_node in ast.walk(tree):
                                if (
                                    isinstance(next_node, (ast.FunctionDef, ast.AsyncFunctionDef))
                                    and next_node.lineno > node.lineno
                                ):
                                    line_end = next_node.lineno - 1
                                    break

                        # Оценка риска
                        risk_level = self._assess_function_risk(node, function_name, file_path)

                        return {
                            "line_start": node.lineno,
                            "line_end": line_end,
                            "risk_level": risk_level,
                            "reason": "Недостижимая функция без вызовов",
                        }

        except Exception as e:
            print(f"❌ Ошибка анализа функции {function_name} в {file_path}: {e}")

        return None

    def _assess_function_risk(
        self, node: ast.FunctionDef, function_name: str, file_path: str
    ) -> str:
        """Оценивает риск удаления функции"""
        # Высокий риск
        if function_name.startswith("__"):  # Magic methods
            return "HIGH"
        if "api" in file_path.lower() or "endpoint" in file_path.lower():
            return "HIGH"
        if any(
            decorator.id == "app"
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Attribute) and hasattr(decorator, "id")
        ):
            return "HIGH"

        # Средний риск
        complexity = self._calculate_complexity(node)
        if complexity > 5:
            return "MEDIUM"
        if isinstance(node, ast.AsyncFunctionDef):
            return "MEDIUM"

        # Низкий риск
        return "LOW"

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Вычисляет сложность функции"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
        return complexity

    def create_removal_plan(self, candidates: list[RemovalCandidate]) -> RemovalPlan:
        """Создаёт план удаления"""
        print("🔍 Создаём план удаления неиспользуемого кода...")

        # Проверяем безопасность каждого кандидата
        safe_candidates = []
        total_lines = 0
        affected_files = set()

        for candidate in candidates:
            print(f"  🔍 Проверяем {candidate.function_name}...")
            safety_check = self.safety_checker.check_removal_safety(candidate)

            candidate.safe_to_remove = safety_check["safe_to_remove"]
            candidate.impact_assessment = f"Безопасность: {safety_check['safety_percentage']:.1f}%"

            if candidate.safe_to_remove and candidate.risk_level == "LOW":
                safe_candidates.append(candidate)
                total_lines += candidate.line_end - candidate.line_start + 1
                affected_files.add(candidate.file_path)

            # Показываем предупреждения
            if safety_check["warnings"]:
                print(f"    ⚠️ Предупреждения: {'; '.join(safety_check['warnings'])}")

        # Создаём резервную копию
        backup_dir = self._create_backup()

        estimated_size = self._estimate_size_reduction(total_lines)

        return RemovalPlan(
            candidates=safe_candidates,
            total_lines_to_remove=total_lines,
            estimated_size_reduction=estimated_size,
            affected_files=list(affected_files),
            backup_directory=backup_dir,
            safety_checks_passed=len(safe_candidates) > 0,
        )

    def _create_backup(self) -> str:
        """Создаёт резервную копию проекта"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_before_cleanup_{timestamp}"
        backup_path = self.project_root.parent / backup_name

        print(f"💾 Создаём резервную копию в {backup_path}...")

        # Копируем только исходный код, исключаем ненужные директории
        exclude_dirs = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "venv",
            "env",
            "node_modules",
            "htmlcov",
        }

        backup_path.mkdir()

        for item in self.project_root.iterdir():
            if item.name not in exclude_dirs:
                if item.is_file():
                    shutil.copy2(item, backup_path)
                else:
                    shutil.copytree(
                        item,
                        backup_path / item.name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                    )

        self.backup_dir = str(backup_path)
        return str(backup_path)

    def _estimate_size_reduction(self, lines_to_remove: int) -> str:
        """Оценивает уменьшение размера кода"""
        # Примерно 50 символов на строку в среднем
        chars_to_remove = lines_to_remove * 50
        kb_to_remove = chars_to_remove / 1024

        if kb_to_remove < 1:
            return f"{chars_to_remove} символов"
        elif kb_to_remove < 1024:
            return f"{kb_to_remove:.1f} KB"
        else:
            return f"{kb_to_remove / 1024:.1f} MB"

    def execute_removal_plan(self, plan: RemovalPlan, dry_run: bool = True) -> dict[str, Any]:
        """Выполняет план удаления"""
        if dry_run:
            print("🔍 ПРОБНЫЙ ЗАПУСК - файлы не будут изменены")
        else:
            print("🗑️ ВЫПОЛНЯЕМ УДАЛЕНИЕ НЕИСПОЛЬЗУЕМОГО КОДА")

        results = {
            "removed_functions": [],
            "modified_files": [],
            "errors": [],
            "lines_removed": 0,
            "size_reduction": plan.estimated_size_reduction,
        }

        # Группируем кандидатов по файлам
        candidates_by_file = {}
        for candidate in plan.candidates:
            if candidate.file_path not in candidates_by_file:
                candidates_by_file[candidate.file_path] = []
            candidates_by_file[candidate.file_path].append(candidate)

        # Обрабатываем каждый файл
        for file_path, file_candidates in candidates_by_file.items():
            try:
                if not dry_run:
                    self._remove_functions_from_file(file_path, file_candidates)

                results["modified_files"].append(file_path)
                results["removed_functions"].extend([c.function_name for c in file_candidates])
                results["lines_removed"] += sum(
                    c.line_end - c.line_start + 1 for c in file_candidates
                )

                print(f"  ✅ Обработан {file_path}: удалено {len(file_candidates)} функций")

            except Exception as e:
                error_msg = f"Ошибка обработки {file_path}: {e}"
                results["errors"].append(error_msg)
                print(f"  ❌ {error_msg}")

        return results

    def _remove_functions_from_file(self, file_path: str, candidates: list[RemovalCandidate]):
        """Удаляет функции из конкретного файла"""
        full_path = self.project_root / file_path

        with open(full_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Сортируем кандидатов по номеру строки (в обратном порядке)
        sorted_candidates = sorted(candidates, key=lambda c: c.line_start, reverse=True)

        # Удаляем функции начиная с конца файла
        for candidate in sorted_candidates:
            start_idx = candidate.line_start - 1  # Индексы с 0
            end_idx = candidate.line_end

            # Удаляем строки
            del lines[start_idx:end_idx]

            print(
                f"    🗑️ Удалена функция {candidate.function_name} (строки {candidate.line_start}-{candidate.line_end})"
            )

        # Записываем изменённый файл
        with open(full_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def run_tests_after_removal(self) -> dict[str, Any]:
        """Запускает тесты после удаления кода"""
        print("🧪 Запускаем тесты после удаления кода...")

        try:
            # Активируем виртуальное окружение и запускаем тесты
            result = subprocess.run(
                ["bash", "-c", "source venv/bin/activate && python -m pytest tests/ -v --tb=short"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 минут таймаут
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "exit_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "errors": "Тесты превысили таймаут 5 минут",
                "exit_code": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": f"Ошибка запуска тестов: {e}",
                "exit_code": -1,
            }


def main():
    """Главная функция"""
    project_root = Path(__file__).parent.parent
    remover = UnusedCodeRemover(project_root)

    print("🗑️ Система удаления неиспользуемого кода BOT_AI_V3")
    print("=" * 50)

    # Загружаем результаты анализа
    analysis_file = project_root / "analysis_results" / "code_chain_analysis.json"

    if not analysis_file.exists():
        print("❌ Файл анализа не найден. Сначала запустите code_chain_analyzer.py")
        return

    # Анализируем кандидатов на удаление
    print("🔍 Анализируем кандидатов на удаление...")
    candidates = remover.analyze_removal_candidates(analysis_file)

    if not candidates:
        print("✅ Неиспользуемых функций не найдено!")
        return

    print(f"📊 Найдено {len(candidates)} кандидатов на удаление")

    # Создаём план удаления
    plan = remover.create_removal_plan(candidates)

    print("\n📋 ПЛАН УДАЛЕНИЯ:")
    print(f"  Функций к удалению: {len(plan.candidates)}")
    print(f"  Строк кода: {plan.total_lines_to_remove}")
    print(f"  Оценка экономии: {plan.estimated_size_reduction}")
    print(f"  Затронутых файлов: {len(plan.affected_files)}")
    print(f"  Резервная копия: {plan.backup_directory}")

    if not plan.safety_checks_passed:
        print("⚠️ Безопасных кандидатов на удаление не найдено")
        return

    # Показываем детали
    print("\n📝 Детали удаления:")
    for candidate in plan.candidates:
        print(f"  🗑️ {candidate.function_name} ({candidate.file_path}:{candidate.line_start})")
        print(f"     Риск: {candidate.risk_level}, {candidate.impact_assessment}")
        print(f"     Причина: {candidate.reason}")

    # Спрашиваем подтверждение
    print("\n❓ Выполнить удаление? (y/N): ", end="")
    response = input().strip().lower()

    if response not in ["y", "yes", "да"]:
        print("❌ Удаление отменено")
        return

    # Сначала пробный запуск
    print("\n🔍 Пробный запуск...")
    dry_results = remover.execute_removal_plan(plan, dry_run=True)

    print(f"  Будет удалено {len(dry_results['removed_functions'])} функций")
    print(f"  Будет изменено {len(dry_results['modified_files'])} файлов")

    if dry_results["errors"]:
        print(f"  ⚠️ Обнаружены ошибки: {len(dry_results['errors'])}")
        for error in dry_results["errors"]:
            print(f"    - {error}")

    print("\n❓ Продолжить с реальным удалением? (y/N): ", end="")
    final_response = input().strip().lower()

    if final_response not in ["y", "yes", "да"]:
        print("❌ Удаление отменено")
        return

    # Реальное удаление
    print("\n🗑️ Выполняем реальное удаление...")
    real_results = remover.execute_removal_plan(plan, dry_run=False)

    # Запускаем тесты
    test_results = remover.run_tests_after_removal()

    # Показываем результаты
    print("\n✅ УДАЛЕНИЕ ЗАВЕРШЕНО!")
    print(f"  Удалено функций: {len(real_results['removed_functions'])}")
    print(f"  Удалено строк: {real_results['lines_removed']}")
    print(f"  Экономия размера: {real_results['size_reduction']}")
    print(f"  Изменённых файлов: {len(real_results['modified_files'])}")

    if test_results["success"]:
        print("  ✅ Тесты прошли успешно!")
    else:
        print("  ❌ Тесты провалились! Проверьте лог:")
        print(f"     {test_results['errors']}")
        print(f"\n💾 Резервная копия доступна в: {plan.backup_directory}")

    # Сохраняем отчёт
    report_file = project_root / "analysis_results" / "removal_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "removal_plan": {
                    "candidates_count": len(plan.candidates),
                    "lines_removed": plan.total_lines_to_remove,
                    "size_reduction": plan.estimated_size_reduction,
                    "affected_files": plan.affected_files,
                    "backup_directory": plan.backup_directory,
                },
                "execution_results": real_results,
                "test_results": test_results,
                "timestamp": datetime.now().isoformat(),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"📄 Отчёт сохранён в {report_file}")


if __name__ == "__main__":
    main()
