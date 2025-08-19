#!/usr/bin/env python3
"""
Высокопроизводительный AST анализатор для BOT_AI_V3
Цель: анализ 1959 функций за < 30 секунд
"""
import ast
import asyncio
import hashlib
import json
import pickle
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent.parent


class HighPerformanceASTAnalyzer:
    """
    Высокопроизводительный анализатор AST с кешированием и параллельностью
    Оптимизации:
    1. Кеширование результатов по хешу файла
    2. Параллельная обработка батчей
    3. Оптимизированный AST walker
    4. Инкрементальный анализ
    """

    def __init__(self, max_workers: int = None, cache_file: str | None = None):
        self.max_workers = max_workers or min(32, (cpu_count() or 1) + 4)
        self.cache = {}
        self.cache_file = cache_file or str(PROJECT_ROOT / "data" / "ast_cache.pickle")
        self.total_files = 0
        self.processed_files = 0

        # Загружаем кеш если есть
        self._load_cache()

    def _load_cache(self):
        """Загружает кеш из файла"""
        try:
            cache_path = Path(self.cache_file)
            if cache_path.exists():
                with open(cache_path, "rb") as f:
                    self.cache = pickle.load(f)
                print(f"📁 Загружен кеш: {len(self.cache)} файлов")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки кеша: {e}")
            self.cache = {}

    def _save_cache(self):
        """Сохраняет кеш в файл"""
        try:
            cache_path = Path(self.cache_file)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "wb") as f:
                pickle.dump(self.cache, f)
            print(f"💾 Кеш сохранён: {len(self.cache)} файлов")
        except Exception as e:
            print(f"⚠️ Ошибка сохранения кеша: {e}")

    async def analyze_codebase_fast(self, project_root: Path) -> dict[str, Any]:
        """Быстрый анализ всей кодовой базы"""
        start_time = time.time()

        print("🚀 Запуск высокопроизводительного анализа AST")
        print(f"   Воркеров: {self.max_workers}")
        print(f"   Проект: {project_root}")

        # Находим все Python файлы
        python_files = [
            f
            for f in project_root.rglob("*.py")
            if not any(
                exclude in str(f)
                for exclude in [
                    "__pycache__",
                    ".venv",
                    "venv",
                    ".git",
                    "node_modules",
                    "htmlcov",
                    ".pytest_cache",
                    "analysis_results",
                    "BOT_AI_V2",
                    "BOT_Trading",
                    "__MACOSX",  # Исключаем старую версию
                ]
            )
        ]

        self.total_files = len(python_files)
        print(f"📁 Найдено Python файлов: {self.total_files}")

        # Проверяем, какие файлы нужно обновить
        files_to_process = []
        cache_hits = 0

        for file_path in python_files:
            file_hash = self._get_file_hash(str(file_path))
            cache_key = f"{file_path}#{file_hash}"

            if cache_key not in self.cache:
                files_to_process.append(file_path)
            else:
                cache_hits += 1

        print(f"🎯 Cache hits: {cache_hits}/{self.total_files}")
        print(f"🔄 Файлов к обработке: {len(files_to_process)}")

        if not files_to_process:
            print("✅ Все файлы в кеше, собираем результаты...")
            return self._merge_cached_results(python_files)

        # Разбиваем на батчи для параллельной обработки
        batch_size = max(1, len(files_to_process) // self.max_workers)
        batches = [
            files_to_process[i : i + batch_size]
            for i in range(0, len(files_to_process), batch_size)
        ]

        print(f"📦 Создано батчей: {len(batches)} (размер: {batch_size})")

        # Параллельная обработка батчей
        loop = asyncio.get_event_loop()

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            print("⚡ Запуск параллельной обработки...")

            tasks = [
                loop.run_in_executor(
                    executor, self._analyze_batch_static, batch, i + 1, len(batches)
                )
                for i, batch in enumerate(batches)
            ]

            batch_results = await asyncio.gather(*tasks)

        # Объединяем результаты и сохраняем в кеш
        final_results = self._merge_results(batch_results, python_files)

        # Сохраняем кеш
        self._save_cache()

        elapsed = time.time() - start_time
        print(f"🎉 Анализ завершён за {elapsed:.2f}с")
        print(f"   Производительность: {self.total_files/elapsed:.1f} файлов/сек")

        return final_results

    @staticmethod
    def _analyze_batch_static(files_batch: list[Path], batch_num: int, total_batches: int) -> dict:
        """Статический метод для обработки батча (для multiprocessing)"""
        analyzer = HighPerformanceASTAnalyzer()
        return analyzer._analyze_batch(files_batch, batch_num, total_batches)

    def _analyze_batch(self, files_batch: list[Path], batch_num: int, total_batches: int) -> dict:
        """Анализирует батч файлов"""
        print(f"📦 Обработка батча {batch_num}/{total_batches} ({len(files_batch)} файлов)")

        batch_results = {
            "functions": {},
            "classes": {},
            "imports": [],  # Это должен быть список, а не словарь
            "call_graph": defaultdict(set),
            "processed_files": [],
        }

        for i, file_path in enumerate(files_batch):
            try:
                file_hash = self._get_file_hash(str(file_path))
                cache_key = f"{file_path}#{file_hash}"

                # Анализируем файл
                file_result = self._analyze_single_file_optimized(file_path)

                # Сохраняем в кеш
                self.cache[cache_key] = file_result

                # Добавляем к результатам батча
                self._merge_file_results(batch_results, file_result)
                batch_results["processed_files"].append(str(file_path))

                # Прогресс
                if (i + 1) % 10 == 0:
                    print(f"   📄 Обработано {i + 1}/{len(files_batch)} файлов в батче {batch_num}")

            except Exception as e:
                print(f"❌ Ошибка в файле {file_path}: {e}")
                continue

        print(f"✅ Батч {batch_num} завершён")
        return batch_results

    @lru_cache(maxsize=10000)
    def _get_file_hash(self, file_path: str) -> str:
        """Хеш файла для кеширования"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return "error"

    def _analyze_single_file_optimized(self, file_path: Path) -> dict:
        """Оптимизированный анализ одного файла"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Быстрая проверка на пустой файл
            if not content.strip():
                return self._empty_file_result()

            tree = ast.parse(content, filename=str(file_path))

            # Быстрый AST walker
            visitor = FastASTVisitor(str(file_path))
            visitor.visit(tree)

            return visitor.get_results()

        except SyntaxError as e:
            return {"error": f"Syntax error: {e}", "functions": {}, "classes": {}, "imports": []}
        except Exception as e:
            return {"error": f"Analysis error: {e}", "functions": {}, "classes": {}, "imports": []}

    def _empty_file_result(self) -> dict:
        """Результат для пустого файла"""
        return {"functions": {}, "classes": {}, "imports": [], "call_graph": {}}

    def _merge_file_results(self, batch_results: dict, file_result: dict):
        """Объединяет результаты файла с результатами батча"""
        batch_results["functions"].update(file_result.get("functions", {}))
        batch_results["classes"].update(file_result.get("classes", {}))

        # Правильно объединяем импорты (это список, а не словарь)
        file_imports = file_result.get("imports", [])
        if isinstance(file_imports, list):
            batch_results["imports"].extend(file_imports)

        # Объединяем call graph
        for caller, callees in file_result.get("call_graph", {}).items():
            if isinstance(callees, (list, set)):
                batch_results["call_graph"][caller].update(callees)

    def _merge_results(self, batch_results: list[dict], all_files: list[Path]) -> dict:
        """Объединяет результаты всех батчей"""
        print("🔗 Объединение результатов батчей...")

        final_result = {
            "functions": {},
            "classes": {},
            "imports": [],  # Список импортов
            "call_graph": defaultdict(set),
            "statistics": {},
            "processed_files": [],
        }

        # Объединяем результаты батчей
        for batch_result in batch_results:
            final_result["functions"].update(batch_result.get("functions", {}))
            final_result["classes"].update(batch_result.get("classes", {}))
            final_result["imports"].extend(batch_result.get("imports", []))  # Расширяем список
            final_result["processed_files"].extend(batch_result.get("processed_files", []))

            # Объединяем call graph
            for caller, callees in batch_result.get("call_graph", {}).items():
                if isinstance(callees, (list, set)):
                    final_result["call_graph"][caller].update(callees)

        # Добавляем кешированные результаты
        cached_results = self._get_cached_results_for_files(all_files)
        final_result["functions"].update(cached_results.get("functions", {}))
        final_result["classes"].update(cached_results.get("classes", {}))
        final_result["imports"].extend(cached_results.get("imports", []))  # Расширяем список

        # Конвертируем set в list для JSON сериализации
        final_result["call_graph"] = {
            caller: list(callees) for caller, callees in final_result["call_graph"].items()
        }

        # Добавляем статистику
        final_result["statistics"] = {
            "total_files": len(all_files),
            "total_functions": len(final_result["functions"]),
            "total_classes": len(final_result["classes"]),
            "total_imports": len(final_result["imports"]),
            "processed_files": len(final_result["processed_files"]),
        }

        print("📊 Финальная статистика:")
        print(f"   Файлов: {final_result['statistics']['total_files']}")
        print(f"   Функций: {final_result['statistics']['total_functions']}")
        print(f"   Классов: {final_result['statistics']['total_classes']}")
        print(f"   Импортов: {final_result['statistics']['total_imports']}")

        return final_result

    def _merge_cached_results(self, all_files: list[Path]) -> dict:
        """Объединяет результаты из кеша для всех файлов"""
        print("📁 Получение результатов из кеша...")

        final_result = {
            "functions": {},
            "classes": {},
            "imports": [],  # Список импортов
            "call_graph": defaultdict(set),
            "statistics": {},
        }

        for file_path in all_files:
            file_hash = self._get_file_hash(str(file_path))
            cache_key = f"{file_path}#{file_hash}"

            if cache_key in self.cache:
                file_result = self.cache[cache_key]
                self._merge_file_results(final_result, file_result)

        # Конвертируем set в list
        final_result["call_graph"] = {
            caller: list(callees) for caller, callees in final_result["call_graph"].items()
        }

        # Статистика
        final_result["statistics"] = {
            "total_files": len(all_files),
            "total_functions": len(final_result["functions"]),
            "total_classes": len(final_result["classes"]),
            "total_imports": len(final_result["imports"]),
            "cache_source": True,
        }

        return final_result

    def _get_cached_results_for_files(self, files: list[Path]) -> dict:
        """Получает кешированные результаты для файлов"""
        cached_result = {
            "functions": {},
            "classes": {},
            "imports": [],  # Список импортов
            "call_graph": defaultdict(set),
        }

        for file_path in files:
            file_hash = self._get_file_hash(str(file_path))
            cache_key = f"{file_path}#{file_hash}"

            if cache_key in self.cache:
                file_result = self.cache[cache_key]
                self._merge_file_results(cached_result, file_result)

        return cached_result


class FastASTVisitor(ast.NodeVisitor):
    """
    Быстрый visitor для AST с минимальными накладными расходами
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.functions = {}
        self.classes = {}
        self.imports = []
        self.call_graph = defaultdict(set)
        self.current_class = None
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Анализ определения функции"""
        func_name = f"{self.file_path}:{node.name}"

        self.functions[func_name] = {
            "name": node.name,
            "line": node.lineno,
            "file": self.file_path,
            "args": [arg.arg for arg in node.args.args],
            "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "is_method": self.current_class is not None,
            "class_name": self.current_class,
        }

        # Сохраняем контекст
        prev_function = self.current_function
        self.current_function = func_name

        # Обходим тело функции для поиска вызовов
        self.generic_visit(node)

        # Восстанавливаем контекст
        self.current_function = prev_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Анализ async функций"""
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Анализ определения класса"""
        class_name = f"{self.file_path}:{node.name}"

        self.classes[class_name] = {
            "name": node.name,
            "line": node.lineno,
            "file": self.file_path,
            "base_classes": [self._get_base_name(base) for base in node.bases],
            "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
            "methods": [],
        }

        # Сохраняем контекст
        prev_class = self.current_class
        self.current_class = node.name

        # Обходим тело класса
        self.generic_visit(node)

        # Восстанавливаем контекст
        self.current_class = prev_class

    def visit_Call(self, node: ast.Call):
        """Анализ вызовов функций"""
        if self.current_function:
            called_func = self._get_call_name(node)
            if called_func:
                self.call_graph[self.current_function].add(called_func)

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        """Анализ импортов"""
        for alias in node.names:
            self.imports.append(
                {"type": "import", "module": alias.name, "alias": alias.asname, "line": node.lineno}
            )

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Анализ from-импортов"""
        for alias in node.names:
            self.imports.append(
                {
                    "type": "from",
                    "module": node.module,
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                }
            )

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Получает имя декоратора"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_attribute_name(decorator.value)}.{decorator.attr}"
        else:
            return str(decorator)

    def _get_base_name(self, base: ast.expr) -> str:
        """Получает имя базового класса"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{self._get_attribute_name(base.value)}.{base.attr}"
        else:
            return str(base)

    def _get_call_name(self, call: ast.Call) -> str | None:
        """Получает имя вызываемой функции"""
        if isinstance(call.func, ast.Name):
            return call.func.id
        elif isinstance(call.func, ast.Attribute):
            return f"{self._get_attribute_name(call.func.value)}.{call.func.attr}"
        else:
            return None

    def _get_attribute_name(self, attr: ast.expr) -> str:
        """Получает имя атрибута"""
        if isinstance(attr, ast.Name):
            return attr.id
        elif isinstance(attr, ast.Attribute):
            return f"{self._get_attribute_name(attr.value)}.{attr.attr}"
        else:
            return "unknown"

    def get_results(self) -> dict:
        """Возвращает результаты анализа"""
        return {
            "functions": self.functions,
            "classes": self.classes,
            "imports": self.imports,
            "call_graph": {k: list(v) for k, v in self.call_graph.items()},
        }


async def main():
    """Главная функция для тестирования"""
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        project_path = PROJECT_ROOT

    analyzer = HighPerformanceASTAnalyzer()

    print(f"🎯 Анализ проекта: {project_path}")
    results = await analyzer.analyze_codebase_fast(project_path)

    # Сохраняем результаты
    output_file = PROJECT_ROOT / "analysis_results" / "fast_ast_analysis.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"💾 Результаты сохранены: {output_file}")

    return results


if __name__ == "__main__":
    asyncio.run(main())
