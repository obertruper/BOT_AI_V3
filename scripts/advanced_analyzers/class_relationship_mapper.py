#!/usr/bin/env python3
"""
Анализатор связей между классами для BOT_AI_V3
Анализирует наследование, композицию, агрегацию, зависимости
"""
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

PROJECT_ROOT = Path(__file__).parent.parent.parent


class ClassRelationshipMapper:
    """
    Анализирует связи между классами:
    - Наследование (inheritance)
    - Композицию (composition)
    - Агрегацию (aggregation)
    - Зависимости (dependencies)
    - Интерфейсы (interfaces)
    - Миксины (mixins)
    """

    def __init__(self):
        self.class_hierarchy = nx.DiGraph()
        self.composition_graph = nx.DiGraph()
        self.dependency_graph = nx.DiGraph()
        self.classes_info = {}
        self.import_map = defaultdict(set)

    def analyze_class_relationships(self, ast_results: dict) -> dict[str, Any]:
        """Анализирует все типы связей между классами"""

        print("🔍 Анализ связей между классами...")

        # Собираем информацию о классах
        self._collect_class_info(ast_results)

        # Анализируем разные типы связей
        relationships = {
            "inheritance": self._analyze_inheritance(ast_results),
            "composition": self._analyze_composition(ast_results),
            "aggregation": self._analyze_aggregation(ast_results),
            "dependencies": self._analyze_dependencies(ast_results),
            "interfaces": self._analyze_interfaces(ast_results),
            "mixins": self._analyze_mixins(ast_results),
            "patterns": self._detect_patterns(ast_results),
        }

        # Создаём граф всех связей
        unified_graph = self._create_unified_graph(relationships)

        # Анализируем архитектурные метрики
        metrics = self._calculate_metrics(relationships)

        # Обнаруживаем проблемы
        issues = self._detect_issues(relationships)

        result = {
            "relationships": relationships,
            "graph": self._graph_to_dict(unified_graph),
            "metrics": metrics,
            "potential_issues": issues,
            "recommendations": self._generate_recommendations(relationships, metrics, issues),
        }

        print("✅ Анализ завершён:")
        print(f"   Классов: {len(self.classes_info)}")
        print(f"   Связей наследования: {len(relationships['inheritance'])}")
        print(f"   Связей композиции: {len(relationships['composition'])}")
        print(f"   Зависимостей: {len(relationships['dependencies'])}")

        return result

    def _collect_class_info(self, ast_results: dict):
        """Собирает информацию о всех классах"""
        self.classes_info = ast_results.get("classes", {})

        # Создаём карту импортов для разрешения зависимостей
        for file_path, imports in ast_results.get("imports", {}).items():
            for import_info in imports:
                if import_info["type"] == "from" and import_info.get("name"):
                    self.import_map[file_path].add(f"{import_info['module']}.{import_info['name']}")
                elif import_info["type"] == "import":
                    self.import_map[file_path].add(import_info["module"])

    def _analyze_inheritance(self, ast_results: dict) -> dict[str, Any]:
        """Анализирует цепочки наследования"""
        print("   📊 Анализ наследования...")

        inheritance_chains = {}
        inheritance_tree = nx.DiGraph()

        for class_name, class_info in self.classes_info.items():
            base_classes = class_info.get("base_classes", [])

            if base_classes:
                # Добавляем в граф наследования
                for base_class in base_classes:
                    inheritance_tree.add_edge(base_class, class_name)

                inheritance_chains[class_name] = {
                    "direct_parents": base_classes,
                    "inheritance_chain": self._trace_inheritance_chain(
                        class_name, inheritance_tree
                    ),
                    "depth": self._calculate_inheritance_depth(class_name, inheritance_tree),
                    "is_abstract": self._is_abstract_class(class_info),
                    "implements_interfaces": self._get_implemented_interfaces(class_info),
                    "overridden_methods": self._find_overridden_methods(class_name, class_info),
                }

        # Находим корневые классы и листовые классы
        root_classes = [
            node for node in inheritance_tree.nodes() if inheritance_tree.in_degree(node) == 0
        ]
        leaf_classes = [
            node for node in inheritance_tree.nodes() if inheritance_tree.out_degree(node) == 0
        ]

        return {
            "chains": inheritance_chains,
            "root_classes": root_classes,
            "leaf_classes": leaf_classes,
            "inheritance_tree": self._graph_to_dict(inheritance_tree),
            "multiple_inheritance": self._find_multiple_inheritance(inheritance_chains),
            "diamond_problem": self._find_diamond_problems(inheritance_tree),
        }

    def _analyze_composition(self, ast_results: dict) -> dict[str, Any]:
        """Анализирует композицию (has-a отношения)"""
        print("   📊 Анализ композиции...")

        composition_patterns = {}

        for class_name, class_info in self.classes_info.items():
            composed_objects = []

            # Ищем атрибуты класса, которые являются экземплярами других классов
            if "attributes" in class_info:
                for attr_name, attr_info in class_info["attributes"].items():
                    if attr_info.get("type_annotation"):
                        composed_objects.append(
                            {
                                "attribute": attr_name,
                                "type": attr_info["type_annotation"],
                                "initialization": attr_info.get("initialization", "unknown"),
                                "is_list": self._is_collection_type(attr_info["type_annotation"]),
                                "is_optional": self._is_optional_type(attr_info["type_annotation"]),
                            }
                        )

            # Анализируем __init__ метод для поиска композиции
            init_compositions = self._analyze_init_composition(class_info)
            composed_objects.extend(init_compositions)

            if composed_objects:
                composition_patterns[class_name] = {
                    "composed_objects": composed_objects,
                    "composition_strength": self._assess_composition_strength(composed_objects),
                    "lifecycle_dependency": self._assess_lifecycle_dependency(composed_objects),
                }

        return composition_patterns

    def _analyze_aggregation(self, ast_results: dict) -> dict[str, Any]:
        """Анализирует агрегацию (uses-a отношения)"""
        print("   📊 Анализ агрегации...")

        aggregation_patterns = {}

        for class_name, class_info in self.classes_info.items():
            aggregated_objects = []

            # Ищем параметры методов, которые передаются извне
            methods = class_info.get("methods", [])
            for method_name in methods:
                method_info = self._get_method_info(class_name, method_name)
                if method_info:
                    method_deps = self._find_method_dependencies(method_info)
                    aggregated_objects.extend(method_deps)

            if aggregated_objects:
                aggregation_patterns[class_name] = {
                    "aggregated_objects": aggregated_objects,
                    "coupling_level": self._assess_coupling_level(aggregated_objects),
                }

        return aggregation_patterns

    def _analyze_dependencies(self, ast_results: dict) -> dict[str, Any]:
        """Анализирует зависимости между классами"""
        print("   📊 Анализ зависимостей...")

        dependencies = {}
        call_graph = ast_results.get("call_graph", {})

        for class_name, class_info in self.classes_info.items():
            class_dependencies = {
                "imports": self._get_class_imports(class_info),
                "method_calls": self._get_external_method_calls(class_name, call_graph),
                "instantiations": self._find_class_instantiations(class_info),
                "static_dependencies": self._find_static_dependencies(class_info),
                "runtime_dependencies": self._find_runtime_dependencies(class_info),
            }

            # Оцениваем силу зависимостей
            dependency_strength = self._assess_dependency_strength(class_dependencies)

            dependencies[class_name] = {
                **class_dependencies,
                "dependency_strength": dependency_strength,
                "is_tightly_coupled": dependency_strength > 0.7,
            }

        return dependencies

    def _analyze_interfaces(self, ast_results: dict) -> dict[str, Any]:
        """Анализирует интерфейсы и абстрактные классы"""
        print("   📊 Анализ интерфейсов...")

        interfaces = {}

        for class_name, class_info in self.classes_info.items():
            if self._is_interface_like(class_info):
                interfaces[class_name] = {
                    "type": self._get_interface_type(class_info),
                    "abstract_methods": self._get_abstract_methods(class_info),
                    "concrete_methods": self._get_concrete_methods(class_info),
                    "implementers": self._find_implementers(class_name),
                    "interface_segregation_score": self._assess_interface_segregation(class_info),
                }

        return interfaces

    def _analyze_mixins(self, ast_results: dict) -> dict[str, Any]:
        """Анализирует миксины"""
        print("   📊 Анализ миксинов...")

        mixins = {}

        for class_name, class_info in self.classes_info.items():
            if self._is_mixin(class_info):
                mixins[class_name] = {
                    "provided_functionality": self._get_mixin_functionality(class_info),
                    "users": self._find_mixin_users(class_name),
                    "conflicts": self._detect_mixin_conflicts(class_name, class_info),
                }

        return mixins

    def _detect_patterns(self, ast_results: dict) -> dict[str, Any]:
        """Обнаруживает архитектурные паттерны"""
        print("   📊 Поиск паттернов...")

        patterns = {
            "singleton": self._find_singleton_pattern(),
            "factory": self._find_factory_pattern(),
            "observer": self._find_observer_pattern(),
            "strategy": self._find_strategy_pattern(),
            "decorator": self._find_decorator_pattern(),
            "adapter": self._find_adapter_pattern(),
            "facade": self._find_facade_pattern(),
        }

        return {k: v for k, v in patterns.items() if v}

    def _create_unified_graph(self, relationships: dict) -> nx.DiGraph:
        """Создаёт единый граф всех связей"""
        graph = nx.DiGraph()

        # Добавляем наследование
        for class_name, info in relationships["inheritance"]["chains"].items():
            for parent in info["direct_parents"]:
                graph.add_edge(parent, class_name, type="inheritance")

        # Добавляем композицию
        for class_name, info in relationships["composition"].items():
            for obj in info["composed_objects"]:
                graph.add_edge(class_name, obj["type"], type="composition")

        # Добавляем зависимости
        for class_name, info in relationships["dependencies"].items():
            for dep in info["method_calls"]:
                graph.add_edge(class_name, dep, type="dependency")

        return graph

    def _calculate_metrics(self, relationships: dict) -> dict[str, Any]:
        """Вычисляет архитектурные метрики"""
        metrics = {
            "inheritance_metrics": self._calculate_inheritance_metrics(
                relationships["inheritance"]
            ),
            "composition_metrics": self._calculate_composition_metrics(
                relationships["composition"]
            ),
            "coupling_metrics": self._calculate_coupling_metrics(relationships["dependencies"]),
            "complexity_metrics": self._calculate_complexity_metrics(relationships),
        }

        return metrics

    def _detect_issues(self, relationships: dict) -> list[dict[str, Any]]:
        """Обнаруживает потенциальные проблемы в архитектуре"""
        issues = []

        # Проблемы наследования
        issues.extend(self._detect_inheritance_issues(relationships["inheritance"]))

        # Проблемы связанности
        issues.extend(self._detect_coupling_issues(relationships["dependencies"]))

        # Проблемы сложности
        issues.extend(self._detect_complexity_issues(relationships))

        return issues

    def _generate_recommendations(
        self, relationships: dict, metrics: dict, issues: list[dict]
    ) -> list[str]:
        """Генерирует рекомендации по улучшению архитектуры"""
        recommendations = []

        # Рекомендации по наследованию
        if metrics["inheritance_metrics"]["max_depth"] > 5:
            recommendations.append("Рассмотрите возможность уменьшения глубины наследования")

        # Рекомендации по связанности
        if metrics["coupling_metrics"]["average_coupling"] > 0.7:
            recommendations.append(
                "Высокая связанность - рассмотрите применение паттерна Dependency Injection"
            )

        # Рекомендации по сложности
        if len(issues) > 10:
            recommendations.append("Множественные проблемы архитектуры - рекомендуется рефакторинг")

        return recommendations

    # Вспомогательные методы (сокращённые для экономии места)

    def _trace_inheritance_chain(self, class_name: str, tree: nx.DiGraph) -> list[str]:
        """Трассирует цепочку наследования"""
        chain = []
        current = class_name
        visited = set()

        while current and current not in visited:
            visited.add(current)
            parents = list(tree.predecessors(current))
            if parents:
                parent = parents[0]  # Берём первого родителя
                chain.append(parent)
                current = parent
            else:
                break

        return chain[::-1]  # Возвращаем от корня к классу

    def _calculate_inheritance_depth(self, class_name: str, tree: nx.DiGraph) -> int:
        """Вычисляет глубину наследования"""
        if not tree.has_node(class_name):
            return 0

        try:
            # Находим путь от корня до класса
            root_nodes = [n for n in tree.nodes() if tree.in_degree(n) == 0]
            max_depth = 0

            for root in root_nodes:
                if nx.has_path(tree, root, class_name):
                    path_length = nx.shortest_path_length(tree, root, class_name)
                    max_depth = max(max_depth, path_length)

            return max_depth
        except:
            return 0

    def _is_abstract_class(self, class_info: dict) -> bool:
        """Проверяет, является ли класс абстрактным"""
        # Упрощённая проверка
        return "ABC" in class_info.get("base_classes", []) or any(
            "abstract" in decorator.lower() for decorator in class_info.get("decorators", [])
        )

    def _find_multiple_inheritance(self, chains: dict) -> list[str]:
        """Находит классы с множественным наследованием"""
        multiple_inheritance = []

        for class_name, info in chains.items():
            if len(info["direct_parents"]) > 1:
                multiple_inheritance.append(class_name)

        return multiple_inheritance

    def _find_diamond_problems(self, tree: nx.DiGraph) -> list[dict]:
        """Находит проблемы ромбовидного наследования"""
        diamonds = []

        # Упрощённый поиск ромбов
        for node in tree.nodes():
            successors = list(tree.successors(node))
            if len(successors) >= 2:
                # Проверяем, есть ли общие потомки
                for i, succ1 in enumerate(successors):
                    for succ2 in successors[i + 1 :]:
                        common_descendants = set(nx.descendants(tree, succ1)) & set(
                            nx.descendants(tree, succ2)
                        )
                        if common_descendants:
                            diamonds.append(
                                {
                                    "root": node,
                                    "branches": [succ1, succ2],
                                    "common_descendants": list(common_descendants),
                                }
                            )

        return diamonds

    def _graph_to_dict(self, graph: nx.DiGraph) -> dict:
        """Преобразует граф в словарь для JSON сериализации"""
        return {
            "nodes": list(graph.nodes()),
            "edges": [
                {"source": u, "target": v, "data": data} for u, v, data in graph.edges(data=True)
            ],
        }

    # Остальные вспомогательные методы (заглушки для полноты)

    def _get_implemented_interfaces(self, class_info: dict) -> list[str]:
        return []

    def _find_overridden_methods(self, class_name: str, class_info: dict) -> list[str]:
        return []

    def _is_collection_type(self, type_annotation: str) -> bool:
        return any(t in type_annotation.lower() for t in ["list", "dict", "set", "tuple"])

    def _is_optional_type(self, type_annotation: str) -> bool:
        return "optional" in type_annotation.lower() or "none" in type_annotation.lower()

    def _analyze_init_composition(self, class_info: dict) -> list[dict]:
        return []

    def _assess_composition_strength(self, composed_objects: list[dict]) -> float:
        return len(composed_objects) / 10.0  # Упрощённая оценка

    def _assess_lifecycle_dependency(self, composed_objects: list[dict]) -> str:
        return "strong" if len(composed_objects) > 5 else "weak"

    def _get_method_info(self, class_name: str, method_name: str) -> dict | None:
        return None

    def _find_method_dependencies(self, method_info: dict) -> list[dict]:
        return []

    def _assess_coupling_level(self, aggregated_objects: list[dict]) -> float:
        return len(aggregated_objects) / 10.0

    def _get_class_imports(self, class_info: dict) -> list[str]:
        return []

    def _get_external_method_calls(self, class_name: str, call_graph: dict) -> list[str]:
        return call_graph.get(class_name, [])

    def _find_class_instantiations(self, class_info: dict) -> list[str]:
        return []

    def _find_static_dependencies(self, class_info: dict) -> list[str]:
        return []

    def _find_runtime_dependencies(self, class_info: dict) -> list[str]:
        return []

    def _assess_dependency_strength(self, dependencies: dict) -> float:
        total_deps = sum(
            len(deps) if isinstance(deps, list) else 0 for deps in dependencies.values()
        )
        return min(total_deps / 20.0, 1.0)

    def _is_interface_like(self, class_info: dict) -> bool:
        return False  # Упрощённая проверка

    def _get_interface_type(self, class_info: dict) -> str:
        return "abstract"

    def _get_abstract_methods(self, class_info: dict) -> list[str]:
        return []

    def _get_concrete_methods(self, class_info: dict) -> list[str]:
        return class_info.get("methods", [])

    def _find_implementers(self, interface_name: str) -> list[str]:
        return []

    def _assess_interface_segregation(self, class_info: dict) -> float:
        return 0.5

    def _is_mixin(self, class_info: dict) -> bool:
        return "mixin" in class_info.get("name", "").lower()

    def _get_mixin_functionality(self, class_info: dict) -> list[str]:
        return class_info.get("methods", [])

    def _find_mixin_users(self, mixin_name: str) -> list[str]:
        return []

    def _detect_mixin_conflicts(self, mixin_name: str, class_info: dict) -> list[str]:
        return []

    def _find_singleton_pattern(self) -> list[str]:
        return []

    def _find_factory_pattern(self) -> list[str]:
        return []

    def _find_observer_pattern(self) -> list[str]:
        return []

    def _find_strategy_pattern(self) -> list[str]:
        return []

    def _find_decorator_pattern(self) -> list[str]:
        return []

    def _find_adapter_pattern(self) -> list[str]:
        return []

    def _find_facade_pattern(self) -> list[str]:
        return []

    def _calculate_inheritance_metrics(self, inheritance_data: dict) -> dict:
        chains = inheritance_data.get("chains", {})
        return {
            "total_classes": len(chains),
            "max_depth": max((info["depth"] for info in chains.values()), default=0),
            "average_depth": (
                sum(info["depth"] for info in chains.values()) / len(chains) if chains else 0
            ),
            "multiple_inheritance_count": len(inheritance_data.get("multiple_inheritance", [])),
        }

    def _calculate_composition_metrics(self, composition_data: dict) -> dict:
        return {
            "classes_with_composition": len(composition_data),
            "average_composed_objects": (
                sum(len(info["composed_objects"]) for info in composition_data.values())
                / len(composition_data)
                if composition_data
                else 0
            ),
        }

    def _calculate_coupling_metrics(self, dependencies_data: dict) -> dict:
        if not dependencies_data:
            return {"average_coupling": 0}

        coupling_scores = [info["dependency_strength"] for info in dependencies_data.values()]
        return {
            "average_coupling": sum(coupling_scores) / len(coupling_scores),
            "highly_coupled_classes": len([s for s in coupling_scores if s > 0.7]),
        }

    def _calculate_complexity_metrics(self, relationships: dict) -> dict:
        total_classes = len(self.classes_info)
        total_relationships = (
            len(relationships["inheritance"]["chains"])
            + len(relationships["composition"])
            + len(relationships["dependencies"])
        )

        return {
            "total_classes": total_classes,
            "total_relationships": total_relationships,
            "relationship_density": total_relationships / max(total_classes, 1),
        }

    def _detect_inheritance_issues(self, inheritance_data: dict) -> list[dict]:
        issues = []

        # Слишком глубокое наследование
        for class_name, info in inheritance_data["chains"].items():
            if info["depth"] > 6:
                issues.append(
                    {
                        "type": "deep_inheritance",
                        "class": class_name,
                        "depth": info["depth"],
                        "severity": "high",
                    }
                )

        return issues

    def _detect_coupling_issues(self, dependencies_data: dict) -> list[dict]:
        issues = []

        # Высокая связанность
        for class_name, info in dependencies_data.items():
            if info["dependency_strength"] > 0.8:
                issues.append(
                    {
                        "type": "high_coupling",
                        "class": class_name,
                        "coupling_score": info["dependency_strength"],
                        "severity": "medium",
                    }
                )

        return issues

    def _detect_complexity_issues(self, relationships: dict) -> list[dict]:
        issues = []

        # Проверяем общую сложность системы
        total_complexity = (
            len(relationships["inheritance"]["chains"])
            + len(relationships["composition"])
            + len(relationships["dependencies"])
        )

        if total_complexity > 100:
            issues.append(
                {
                    "type": "high_system_complexity",
                    "total_relationships": total_complexity,
                    "severity": "high",
                }
            )

        return issues


async def main():
    """Главная функция для тестирования"""
    # Загружаем результаты AST анализа
    ast_results_file = PROJECT_ROOT / "analysis_results" / "fast_ast_analysis.json"

    if not ast_results_file.exists():
        print("❌ Сначала запустите AST анализатор:")
        print("   python scripts/advanced_analyzers/ast_performance_analyzer.py")
        return

    with open(ast_results_file, encoding="utf-8") as f:
        ast_results = json.load(f)

    # Анализируем связи классов
    mapper = ClassRelationshipMapper()
    relationships = mapper.analyze_class_relationships(ast_results)

    # Сохраняем результаты
    output_file = PROJECT_ROOT / "analysis_results" / "class_relationships.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(relationships, f, indent=2, ensure_ascii=False)

    print(f"💾 Результаты сохранены: {output_file}")

    return relationships


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
