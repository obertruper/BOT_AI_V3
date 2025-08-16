"""
Архитектурный агент для анализа и улучшения архитектуры проекта
"""

import ast
import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from ..claude_code_sdk import ClaudeCodeOptions, ClaudeCodeSDK, ThinkingMode
from ..utils import get_mcp_manager


@dataclass
class ModuleInfo:
    """Информация о модуле проекта"""

    path: Path
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    complexity: int = 0
    lines_of_code: int = 0
    docstring_coverage: float = 0.0


@dataclass
class ArchitectureAnalysis:
    """Результат анализа архитектуры"""

    modules: dict[str, ModuleInfo]
    dependency_graph: nx.DiGraph
    circular_dependencies: list[list[str]]
    code_smells: list[dict[str, Any]]
    metrics: dict[str, Any]
    recommendations: list[str]


class ArchitectAgent:
    """Агент для анализа и улучшения архитектуры кода"""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path.cwd()
        self.sdk = ClaudeCodeSDK()
        self.mcp_manager = get_mcp_manager()
        self.modules: dict[str, ModuleInfo] = {}
        self.dependency_graph = nx.DiGraph()

    async def analyze_architecture(self) -> ArchitectureAnalysis:
        """Полный анализ архитектуры проекта"""
        # Сканируем все Python файлы
        await self._scan_project_structure()

        # Анализируем зависимости
        self._build_dependency_graph()

        # Находим проблемы
        circular_deps = self._find_circular_dependencies()
        code_smells = await self._detect_code_smells()

        # Вычисляем метрики
        metrics = self._calculate_metrics()

        # Генерируем рекомендации через Claude
        recommendations = await self._generate_recommendations(circular_deps, code_smells, metrics)

        return ArchitectureAnalysis(
            modules=self.modules,
            dependency_graph=self.dependency_graph,
            circular_dependencies=circular_deps,
            code_smells=code_smells,
            metrics=metrics,
            recommendations=recommendations,
        )

    async def _scan_project_structure(self):
        """Сканировать структуру проекта"""
        python_files = list(self.project_root.rglob("*.py"))

        # Исключаем виртуальные окружения и кеш
        python_files = [
            f
            for f in python_files
            if not any(part in f.parts for part in ["venv", "__pycache__", ".git", "node_modules"])
        ]

        for file_path in python_files:
            module_info = await self._analyze_module(file_path)
            relative_path = file_path.relative_to(self.project_root)
            self.modules[str(relative_path)] = module_info

    async def _analyze_module(self, file_path: Path) -> ModuleInfo:
        """Анализировать отдельный модуль"""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            module_info = ModuleInfo(path=file_path)
            module_info.lines_of_code = len(content.splitlines())

            # Анализируем AST
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_info.imports.append(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_info.imports.append(node.module)

                elif isinstance(node, ast.ClassDef):
                    module_info.classes.append(node.name)

                elif isinstance(node, ast.FunctionDef):
                    module_info.functions.append(node.name)

            # Вычисляем сложность
            module_info.complexity = self._calculate_cyclomatic_complexity(tree)

            # Проверяем покрытие docstring
            module_info.docstring_coverage = self._calculate_docstring_coverage(tree)

            return module_info

        except Exception:
            # Возвращаем пустой модуль при ошибке
            return ModuleInfo(path=file_path)

    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """Вычислить цикломатическую сложность"""
        complexity = 1  # Базовая сложность

        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1

        return complexity

    def _calculate_docstring_coverage(self, tree: ast.AST) -> float:
        """Вычислить процент покрытия docstring"""
        total_items = 0
        documented_items = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                total_items += 1
                if ast.get_docstring(node):
                    documented_items += 1

        return documented_items / total_items if total_items > 0 else 0.0

    def _build_dependency_graph(self):
        """Построить граф зависимостей"""
        for module_name, module_info in self.modules.items():
            self.dependency_graph.add_node(module_name)

            for imp in module_info.imports:
                # Проверяем, является ли это внутренним импортом
                if self._is_internal_import(imp):
                    target_module = self._resolve_import(imp)
                    if target_module in self.modules:
                        self.dependency_graph.add_edge(module_name, target_module)

    def _is_internal_import(self, import_name: str) -> bool:
        """Проверить, является ли импорт внутренним"""
        # Простая эвристика: если начинается с точки или содержит имя проекта
        return import_name.startswith(".") or "bot_trading" in import_name.lower()

    def _resolve_import(self, import_name: str) -> str:
        """Разрешить импорт в путь модуля"""
        # Упрощенная логика разрешения импортов
        if import_name.startswith("."):
            return import_name[1:]
        return import_name.replace(".", "/")

    def _find_circular_dependencies(self) -> list[list[str]]:
        """Найти циклические зависимости"""
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            return cycles
        except:
            return []

    async def _detect_code_smells(self) -> list[dict[str, Any]]:
        """Обнаружить code smells"""
        code_smells = []

        for module_name, module_info in self.modules.items():
            # Слишком большие модули
            if module_info.lines_of_code > 500:
                code_smells.append(
                    {
                        "type": "large_module",
                        "module": module_name,
                        "lines": module_info.lines_of_code,
                        "severity": "medium",
                    }
                )

            # Высокая сложность
            if module_info.complexity > 20:
                code_smells.append(
                    {
                        "type": "high_complexity",
                        "module": module_name,
                        "complexity": module_info.complexity,
                        "severity": "high",
                    }
                )

            # Низкое покрытие docstring
            if module_info.docstring_coverage < 0.5:
                code_smells.append(
                    {
                        "type": "low_documentation",
                        "module": module_name,
                        "coverage": module_info.docstring_coverage,
                        "severity": "low",
                    }
                )

        return code_smells

    def _calculate_metrics(self) -> dict[str, Any]:
        """Вычислить метрики проекта"""
        total_loc = sum(m.lines_of_code for m in self.modules.values())
        total_modules = len(self.modules)
        avg_complexity = (
            sum(m.complexity for m in self.modules.values()) / total_modules
            if total_modules > 0
            else 0
        )
        avg_doc_coverage = (
            sum(m.docstring_coverage for m in self.modules.values()) / total_modules
            if total_modules > 0
            else 0
        )

        return {
            "total_lines_of_code": total_loc,
            "total_modules": total_modules,
            "average_complexity": round(avg_complexity, 2),
            "average_doc_coverage": round(avg_doc_coverage * 100, 2),
            "total_classes": sum(len(m.classes) for m in self.modules.values()),
            "total_functions": sum(len(m.functions) for m in self.modules.values()),
            "dependency_graph_density": (
                nx.density(self.dependency_graph) if self.dependency_graph else 0
            ),
        }

    async def _generate_recommendations(
        self,
        circular_deps: list[list[str]],
        code_smells: list[dict[str, Any]],
        metrics: dict[str, Any],
    ) -> list[str]:
        """Генерировать рекомендации через Claude"""
        options = ClaudeCodeOptions(
            system_prompt="""Вы архитектор программного обеспечения.
            Анализируйте метрики и предлагайте конкретные улучшения архитектуры.""",
            thinking_mode=ThinkingMode.THINK_HARD,
            max_turns=1,
        )

        prompt = f"""Проанализируйте архитектуру проекта и предложите улучшения:

        Метрики:
        {json.dumps(metrics, indent=2)}

        Циклические зависимости: {len(circular_deps)}
        Code smells: {len(code_smells)}

        Детали code smells:
        {json.dumps(code_smells[:10], indent=2)}  # Первые 10

        Предложите 5-7 конкретных рекомендаций по улучшению архитектуры."""

        try:
            result = await self.sdk.query(prompt, options)
            # Парсим рекомендации из ответа
            recommendations = result.strip().split("\n")
            return [r.strip() for r in recommendations if r.strip()]
        except:
            return ["Не удалось сгенерировать рекомендации"]

    async def generate_architecture_diagram(self) -> str:
        """Генерировать диаграмму архитектуры в формате Mermaid"""
        if not self.modules:
            await self._scan_project_structure()
            self._build_dependency_graph()

        # Группируем модули по пакетам
        packages = defaultdict(list)
        for module_name in self.modules:
            package = module_name.split("/")[0] if "/" in module_name else "root"
            packages[package].append(module_name)

        # Генерируем Mermaid диаграмму
        mermaid = ["graph TD"]

        # Добавляем узлы
        for package, modules in packages.items():
            mermaid.append(f"    subgraph {package}")
            for module in modules[:5]:  # Ограничиваем для читаемости
                node_id = module.replace("/", "_").replace(".", "_")
                mermaid.append(f"        {node_id}[{module}]")
            if len(modules) > 5:
                mermaid.append(f"        ..._{package}[... и еще {len(modules) - 5}]")
            mermaid.append("    end")

        # Добавляем связи (ограничиваем количество)
        edges_shown = 0
        for edge in self.dependency_graph.edges():
            if edges_shown < 20:  # Показываем только первые 20 связей
                source_id = edge[0].replace("/", "_").replace(".", "_")
                target_id = edge[1].replace("/", "_").replace(".", "_")
                mermaid.append(f"    {source_id} --> {target_id}")
                edges_shown += 1

        return "\n".join(mermaid)

    async def suggest_refactoring(self, module_path: str) -> dict[str, Any]:
        """Предложить рефакторинг для конкретного модуля"""
        options = ClaudeCodeOptions(
            system_prompt="""Вы эксперт по рефакторингу.
            Анализируйте код и предлагайте конкретные улучшения.""",
            thinking_mode=ThinkingMode.THINK,
            allowed_tools=["Read", "Task"],
            max_turns=3,
        )

        prompt = f"""Проанализируйте модуль {module_path} и предложите рефакторинг:

        1. Найдите дублирование кода
        2. Предложите лучшие паттерны проектирования
        3. Улучшите читаемость
        4. Оптимизируйте производительность

        Предоставьте конкретные примеры кода."""

        result = await self.sdk.query(prompt, options)

        return {"module": module_path, "suggestions": result}


# Функции для быстрого доступа
async def analyze_project_architecture(
    project_root: str | None = None,
) -> ArchitectureAnalysis:
    """Быстрый анализ архитектуры проекта"""
    root = Path(project_root) if project_root else Path.cwd()
    agent = ArchitectAgent(root)
    return await agent.analyze_architecture()


async def generate_architecture_report(
    output_file: str = "architecture_report.md",
) -> str:
    """Генерировать отчет об архитектуре"""
    analysis = await analyze_project_architecture()

    report = [
        "# Отчет об архитектуре проекта",
        f"\nДата: {Path(output_file).stem}",
        "\n## Метрики проекта",
        f"- Всего строк кода: {analysis.metrics['total_lines_of_code']}",
        f"- Количество модулей: {analysis.metrics['total_modules']}",
        f"- Средняя сложность: {analysis.metrics['average_complexity']}",
        f"- Покрытие документацией: {analysis.metrics['average_doc_coverage']}%",
        "\n## Проблемы",
        f"\n### Циклические зависимости ({len(analysis.circular_dependencies)})",
    ]

    for cycle in analysis.circular_dependencies[:5]:
        report.append(f"- {' -> '.join(cycle)}")

    report.extend(
        [
            f"\n### Code Smells ({len(analysis.code_smells)})",
        ]
    )

    for smell in analysis.code_smells[:10]:
        report.append(f"- [{smell['severity']}] {smell['type']} в {smell['module']}")

    report.extend(
        [
            "\n## Рекомендации",
        ]
    )

    for i, rec in enumerate(analysis.recommendations, 1):
        report.append(f"{i}. {rec}")

    content = "\n".join(report)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)

    return output_file


if __name__ == "__main__":
    # Пример использования
    async def main():
        # Анализ архитектуры
        analysis = await analyze_project_architecture()
        print(f"Найдено модулей: {len(analysis.modules)}")
        print(f"Циклических зависимостей: {len(analysis.circular_dependencies)}")

        # Генерация отчета
        report_file = await generate_architecture_report()
        print(f"Отчет сохранен в: {report_file}")

    asyncio.run(main())
