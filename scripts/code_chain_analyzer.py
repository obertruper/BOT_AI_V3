#!/usr/bin/env python3
"""
Анализатор цепочки кода для BOT_AI_V3
Строит граф зависимостей и находит неиспользуемый код
"""
import ast
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import networkx as nx

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class FunctionNode:
    """Узел функции в графе зависимостей"""

    name: str
    file_path: str
    line_number: int
    is_async: bool
    is_entry_point: bool
    calls: list[str]  # Функции которые вызывает
    called_by: list[str]  # Функции которые её вызывают
    complexity: int
    is_tested: bool
    is_reachable: bool = False
    execution_count: int = 0


@dataclass
class CodeChainAnalysis:
    """Результат анализа цепочки кода"""

    total_functions: int
    reachable_functions: int
    unreachable_functions: list[str]
    entry_points: list[str]
    critical_paths: list[list[str]]
    unused_code_candidates: list[str]
    dependency_graph: dict[str, list[str]]
    coverage_gaps: dict[str, float]


class CallGraphBuilder:
    """Строитель графа вызовов функций"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.functions: dict[str, FunctionNode] = {}
        self.imports: dict[str, set[str]] = defaultdict(set)
        self.entry_points = [
            "unified_launcher.py:main",
            "main.py:main",
            "unified_launcher.py:UnifiedLauncher.start",
            "core/system/orchestrator.py:SystemOrchestrator.start_all",
            "trading/engine.py:TradingEngine.process_signal",
            "ml/ml_manager.py:MLManager.get_prediction",
            "api/main.py:create_app",
        ]

    def analyze_file(self, file_path: Path) -> list[FunctionNode]:
        """Анализирует файл и извлекает функции с их вызовами"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            functions = []

            # Извлекаем импорты
            imports = self._extract_imports(tree)
            rel_path = str(file_path.relative_to(self.project_root))
            self.imports[rel_path] = imports

            # Извлекаем функции
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_node = self._extract_function_node(node, file_path)
                    if func_node:
                        functions.append(func_node)
                        func_key = f"{rel_path}:{func_node.name}"
                        self.functions[func_key] = func_node

            return functions

        except Exception as e:
            print(f"Ошибка анализа {file_path}: {e}")
            return []

    def _extract_imports(self, tree: ast.AST) -> set[str]:
        """Извлекает все импорты из файла"""
        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        imports.add(f"{node.module}.{alias.name}")

        return imports

    def _extract_function_node(self, node: ast.FunctionDef, file_path: Path) -> FunctionNode | None:
        """Извлекает информацию о функции"""
        if node.name.startswith("_") and not node.name.startswith("__"):
            return None  # Пропускаем приватные функции

        rel_path = str(file_path.relative_to(self.project_root))

        # Находим все вызовы функций
        calls = self._extract_function_calls(node)

        # Проверяем является ли entry point
        func_key = f"{rel_path}:{node.name}"
        is_entry = any(ep in func_key for ep in self.entry_points)

        # Вычисляем сложность
        complexity = self._calculate_complexity(node)

        # Проверяем есть ли тесты
        is_tested = self._check_has_tests(node.name, file_path)

        return FunctionNode(
            name=node.name,
            file_path=rel_path,
            line_number=node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_entry_point=is_entry,
            calls=calls,
            called_by=[],
            complexity=complexity,
            is_tested=is_tested,
        )

    def _extract_function_calls(self, node: ast.FunctionDef) -> list[str]:
        """Извлекает все вызовы функций из тела функции"""
        calls = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child)
                if call_name:
                    calls.append(call_name)

        return calls

    def _get_call_name(self, call_node: ast.Call) -> str | None:
        """Получает имя вызываемой функции"""
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            # Для методов типа obj.method()
            if isinstance(call_node.func.value, ast.Name):
                return f"{call_node.func.value.id}.{call_node.func.attr}"
            else:
                return call_node.func.attr
        return None

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Вычисляет цикломатическую сложность"""
        complexity = 1

        for child in ast.walk(node):
            if (
                isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor))
                or isinstance(child, ast.ExceptHandler)
                or isinstance(child, (ast.And, ast.Or))
            ):
                complexity += 1

        return complexity

    def _check_has_tests(self, func_name: str, file_path: Path) -> bool:
        """Проверяет есть ли тесты для функции"""
        rel_path = file_path.relative_to(self.project_root)
        test_file = self.project_root / "tests" / f"test_{rel_path.name}"

        if not test_file.exists():
            return False

        try:
            with open(test_file) as f:
                content = f.read()
                return f"test_{func_name}" in content
        except:
            return False

    def build_call_graph(self) -> nx.DiGraph:
        """Строит граф вызовов функций"""
        # Сканируем все Python файлы
        python_files = list(self.project_root.rglob("*.py"))
        source_files = [
            f
            for f in python_files
            if not any(part.startswith((".", "__pycache__", "test_")) for part in f.parts)
        ]

        print(f"🔍 Анализируем {len(source_files)} файлов...")

        for file_path in source_files:
            self.analyze_file(file_path)

        # Строим граф зависимостей
        graph = nx.DiGraph()

        # Добавляем узлы
        for func_key, func_node in self.functions.items():
            graph.add_node(func_key, **asdict(func_node))

        # Добавляем рёбра (вызовы)
        for func_key, func_node in self.functions.items():
            for call in func_node.calls:
                # Ищем соответствующую функцию
                target_func = self._resolve_call_target(call, func_node.file_path)
                if target_func and target_func in self.functions:
                    graph.add_edge(func_key, target_func)
                    # Обновляем called_by
                    self.functions[target_func].called_by.append(func_key)

        return graph

    def _resolve_call_target(self, call: str, from_file: str) -> str | None:
        """Разрешает вызов функции в конкретный target"""
        # Простое разрешение - ищем в том же файле
        same_file_target = f"{from_file}:{call}"
        if same_file_target in self.functions:
            return same_file_target

        # Ищем в импортах
        imports = self.imports.get(from_file, set())
        for imp in imports:
            if call in imp:
                # Пытаемся найти файл импорта
                possible_target = self._find_import_target(imp, call)
                if possible_target:
                    return possible_target

        # Ищем по частичному совпадению имени
        for func_key in self.functions.keys():
            if func_key.endswith(f":{call}"):
                return func_key

        return None

    def _find_import_target(self, import_path: str, call: str) -> str | None:
        """Находит target функции в импорте"""
        # Упрощённая логика - можно улучшить
        parts = import_path.split(".")
        if len(parts) >= 2:
            file_part = "/".join(parts[:-1]) + ".py"
            func_part = parts[-1]
            target = f"{file_part}:{func_part}"
            if target in self.functions:
                return target

        return None


class DeadCodeDetector:
    """Детектор неиспользуемого кода"""

    def __init__(self, call_graph: nx.DiGraph, functions: dict[str, FunctionNode]):
        self.call_graph = call_graph
        self.functions = functions

    def find_reachable_functions(self, entry_points: list[str]) -> set[str]:
        """Находит все достижимые функции от entry points"""
        reachable = set()

        # Находим реальные entry points в графе
        actual_entry_points = []
        for node in self.call_graph.nodes():
            node_data = self.call_graph.nodes[node]
            if node_data.get("is_entry_point", False):
                actual_entry_points.append(node)

        if not actual_entry_points:
            # Если не найдены entry points, ищем по именам файлов
            for node in self.call_graph.nodes():
                if any(ep in node for ep in entry_points):
                    actual_entry_points.append(node)

        print(f"🎯 Найдено {len(actual_entry_points)} entry points")

        # Обход в глубину от каждой entry point
        for entry in actual_entry_points:
            if entry in self.call_graph:
                reachable.update(nx.descendants(self.call_graph, entry))
                reachable.add(entry)  # Добавляем саму entry point

        return reachable

    def find_unreachable_functions(self, entry_points: list[str]) -> list[str]:
        """Находит недостижимые функции"""
        reachable = self.find_reachable_functions(entry_points)
        all_functions = set(self.call_graph.nodes())
        unreachable = all_functions - reachable

        # Обновляем флаг reachable
        for func_key in self.functions:
            self.functions[func_key].is_reachable = func_key in reachable

        return list(unreachable)

    def find_dead_code_candidates(self) -> list[dict[str, Any]]:
        """Находит кандидатов на удаление"""
        candidates = []

        for func_key, func_node in self.functions.items():
            if not func_node.is_reachable and not func_node.is_entry_point:
                risk_level = self._assess_removal_risk(func_node)
                candidates.append(
                    {
                        "function": func_key,
                        "file": func_node.file_path,
                        "line": func_node.line_number,
                        "risk_level": risk_level,
                        "reason": self._get_removal_reason(func_node, risk_level),
                        "safe_to_remove": risk_level == "LOW",
                    }
                )

        # Сортируем по уровню риска
        risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        candidates.sort(key=lambda x: risk_order[x["risk_level"]])

        return candidates

    def _assess_removal_risk(self, func_node: FunctionNode) -> str:
        """Оценивает риск удаления функции"""
        # Высокий риск
        if func_node.name.startswith("__"):  # Magic methods
            return "HIGH"
        if "api" in func_node.file_path.lower():  # API endpoints
            return "HIGH"
        if "test" in func_node.name.lower():  # Test functions
            return "HIGH"

        # Средний риск
        if func_node.complexity > 5:  # Сложные функции
            return "MEDIUM"
        if func_node.is_async:  # Async функции
            return "MEDIUM"
        if len(func_node.calls) > 10:  # Много вызовов
            return "MEDIUM"

        # Низкий риск
        return "LOW"

    def _get_removal_reason(self, func_node: FunctionNode, risk_level: str) -> str:
        """Возвращает причину для удаления"""
        reasons = []

        if not func_node.is_reachable:
            reasons.append("недостижима от entry points")
        if not func_node.is_tested:
            reasons.append("не покрыта тестами")
        if func_node.execution_count == 0:
            reasons.append("никогда не выполнялась")

        return "; ".join(reasons) if reasons else "неиспользуемая функция"


class CodeChainAnalyzer:
    """Главный анализатор цепочки кода"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.call_graph_builder = CallGraphBuilder(project_root)
        self.call_graph = None
        self.dead_code_detector = None

    def full_analysis(self) -> CodeChainAnalysis:
        """Полный анализ цепочки кода"""
        print("🔍 Запускаем полный анализ цепочки кода...")

        # 1. Строим граф вызовов
        print("📊 Строим граф вызовов функций...")
        self.call_graph = self.call_graph_builder.build_call_graph()

        # 2. Инициализируем детектор мёртвого кода
        self.dead_code_detector = DeadCodeDetector(
            self.call_graph, self.call_graph_builder.functions
        )

        # 3. Находим недостижимые функции
        print("🔍 Ищем недостижимые функции...")
        entry_points = [
            "unified_launcher.py:main",
            "main.py:main",
            "unified_launcher.py:UnifiedLauncher.start",
        ]
        unreachable = self.dead_code_detector.find_unreachable_functions(entry_points)

        # 4. Находим кандидатов на удаление
        print("🗑️ Ищем кандидатов на удаление...")
        dead_code_candidates = self.dead_code_detector.find_dead_code_candidates()

        # 5. Находим критические пути
        print("🎯 Анализируем критические пути...")
        critical_paths = self._find_critical_paths()

        # 6. Анализируем покрытие
        print("📈 Анализируем покрытие тестами...")
        coverage_gaps = self._analyze_coverage_gaps()

        # 7. Строим граф зависимостей
        dependency_graph = self._build_dependency_graph()

        total_functions = len(self.call_graph_builder.functions)
        reachable_count = total_functions - len(unreachable)

        return CodeChainAnalysis(
            total_functions=total_functions,
            reachable_functions=reachable_count,
            unreachable_functions=unreachable,
            entry_points=entry_points,
            critical_paths=critical_paths,
            unused_code_candidates=[c["function"] for c in dead_code_candidates],
            dependency_graph=dependency_graph,
            coverage_gaps=coverage_gaps,
        )

    def _find_critical_paths(self) -> list[list[str]]:
        """Находит критические пути выполнения"""
        critical_paths = []

        # Основные workflow
        workflows = [
            # Торговый workflow
            ["unified_launcher.py", "trading/engine.py", "trading/order_manager.py", "exchanges/"],
            # ML workflow
            ["ml/ml_manager.py", "ml/logic/patchtst_model.py", "trading/signal_processor.py"],
            # API workflow
            ["api/main.py", "api/endpoints/", "database/connections/"],
            # WebSocket workflow
            ["web/websocket/", "trading/engine.py", "api/real_time/"],
        ]

        for workflow in workflows:
            path = self._trace_execution_path(workflow)
            if path:
                critical_paths.append(path)

        return critical_paths

    def _trace_execution_path(self, workflow_pattern: list[str]) -> list[str]:
        """Отслеживает путь выполнения для workflow"""
        path = []

        for pattern in workflow_pattern:
            # Находим функции соответствующие паттерну
            matching_functions = [
                func_key
                for func_key in self.call_graph_builder.functions.keys()
                if pattern in func_key
            ]

            if matching_functions:
                # Берём первую найденную (можно улучшить логику выбора)
                path.append(matching_functions[0])

        return path

    def _analyze_coverage_gaps(self) -> dict[str, float]:
        """Анализирует пробелы в покрытии"""
        coverage_by_module = defaultdict(lambda: {"total": 0, "tested": 0})

        for func_key, func_node in self.call_graph_builder.functions.items():
            module = func_node.file_path.split("/")[0]
            coverage_by_module[module]["total"] += 1
            if func_node.is_tested:
                coverage_by_module[module]["tested"] += 1

        coverage_gaps = {}
        for module, stats in coverage_by_module.items():
            if stats["total"] > 0:
                coverage_gaps[module] = (stats["tested"] / stats["total"]) * 100
            else:
                coverage_gaps[module] = 0.0

        return coverage_gaps

    def _build_dependency_graph(self) -> dict[str, list[str]]:
        """Строит граф зависимостей"""
        dependency_graph = {}

        for func_key, func_node in self.call_graph_builder.functions.items():
            dependency_graph[func_key] = func_node.calls

        return dependency_graph

    def save_analysis(self, analysis: CodeChainAnalysis, output_file: Path):
        """Сохраняет результаты анализа"""
        analysis_data = {
            "total_functions": analysis.total_functions,
            "reachable_functions": analysis.reachable_functions,
            "unreachable_functions": analysis.unreachable_functions,
            "entry_points": analysis.entry_points,
            "critical_paths": analysis.critical_paths,
            "unused_code_candidates": analysis.unused_code_candidates,
            "dependency_graph": analysis.dependency_graph,
            "coverage_gaps": analysis.coverage_gaps,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)

        print(f"💾 Анализ сохранён в {output_file}")

    def save_graph(self, output_file: Path):
        """Сохраняет граф в формате GraphML для визуализации"""
        if self.call_graph:
            nx.write_graphml(self.call_graph, output_file)
            print(f"📊 Граф сохранён в {output_file}")


def main():
    """Главная функция"""
    project_root = Path(__file__).parent.parent
    analyzer = CodeChainAnalyzer(project_root)

    print("🚀 Анализатор цепочки кода BOT_AI_V3")
    print("=" * 50)

    # Запускаем полный анализ
    analysis = analyzer.full_analysis()

    # Выводим результаты
    print("\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
    print(f"  Всего функций: {analysis.total_functions}")
    print(f"  Достижимых: {analysis.reachable_functions}")
    print(f"  Недостижимых: {len(analysis.unreachable_functions)}")
    print(f"  Кандидатов на удаление: {len(analysis.unused_code_candidates)}")

    print("\n📈 Покрытие по модулям:")
    for module, coverage in analysis.coverage_gaps.items():
        print(f"  {module}: {coverage:.1f}%")

    print(f"\n🎯 Критические пути ({len(analysis.critical_paths)}):")
    for i, path in enumerate(analysis.critical_paths, 1):
        print(f"  {i}. {' → '.join([p.split(':')[0] for p in path[:3]])}...")

    # Сохраняем результаты
    output_dir = project_root / "analysis_results"
    output_dir.mkdir(exist_ok=True)

    analyzer.save_analysis(analysis, output_dir / "code_chain_analysis.json")
    analyzer.save_graph(output_dir / "call_graph.graphml")

    print(f"\n✅ Анализ завершён! Результаты в {output_dir}/")
    print("📄 JSON отчёт: code_chain_analysis.json")
    print("📊 Граф: call_graph.graphml (можно открыть в Gephi/Cytoscape)")


if __name__ == "__main__":
    main()
