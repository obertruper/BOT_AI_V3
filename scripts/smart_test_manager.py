#!/usr/bin/env python3
"""
Умный менеджер тестов для BOT_AI_V3
- Автоматически находит и обновляет существующие тесты
- Создаёт новые тесты для непокрытых функций
- Мониторит изменения и обновляет тесты
"""

import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

import click


class SmartTestManager:
    """Интеллектуальный менеджер тестов"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.tests_dir = project_root / "tests"
        self.cache_file = self.tests_dir / ".test_cache.json"
        self.coverage_file = self.tests_dir / ".coverage_tracking.json"
        self.test_mapping = {}
        self.coverage_data = {}

        # Загружаем кэш если есть
        self.load_cache()

    def load_cache(self):
        """Загружает кэш тестов и покрытия"""
        if self.cache_file.exists():
            with open(self.cache_file) as f:
                self.test_mapping = json.load(f)

        if self.coverage_file.exists():
            with open(self.coverage_file) as f:
                self.coverage_data = json.load(f)

    def save_cache(self):
        """Сохраняет кэш"""
        with open(self.cache_file, "w") as f:
            json.dump(self.test_mapping, f, indent=2)

        with open(self.coverage_file, "w") as f:
            json.dump(self.coverage_data, f, indent=2)

    def scan_project(self) -> dict[str, list[str]]:
        """Сканирует проект и находит все функции бизнес-логики"""

        business_files = {}

        # Паттерны для поиска бизнес-логики
        patterns = [
            "trading/**/*.py",
            "ml/**/*.py",
            "exchanges/**/*.py",
            "strategies/**/*.py",
            "core/**/*.py",
            "database/repositories/**/*.py",
        ]

        for pattern in patterns:
            for file_path in self.project_root.glob(pattern):
                if "__pycache__" in str(file_path):
                    continue

                rel_path = file_path.relative_to(self.project_root)
                functions = self.extract_functions(file_path)
                if functions:
                    business_files[str(rel_path)] = functions

        return business_files

    def extract_functions(self, file_path: Path) -> list[str]:
        """Извлекает функции из файла"""
        functions = []

        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not item.name.startswith("_") or item.name == "__init__":
                                functions.append(f"{node.name}.{item.name}")

                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("_"):
                        functions.append(node.name)

        except Exception as e:
            print(f"⚠️ Ошибка при анализе {file_path}: {e}")

        return functions

    def find_existing_tests(self) -> dict[str, str]:
        """Находит существующие тесты"""
        existing_tests = {}

        for test_file in self.tests_dir.rglob("test_*.py"):
            if "__pycache__" in str(test_file):
                continue

            # Анализируем какие функции покрыты этим тестом
            covered = self.analyze_test_coverage(test_file)
            for func in covered:
                existing_tests[func] = str(test_file.relative_to(self.project_root))

        return existing_tests

    def analyze_test_coverage(self, test_file: Path) -> list[str]:
        """Анализирует какие функции покрывает тестовый файл"""
        covered_functions = []

        try:
            with open(test_file, encoding="utf-8") as f:
                content = f.read()

            # Ищем импорты тестируемых модулей
            import_pattern = r"from\s+([\w\.]+)\s+import\s+([\w\,\s]+)"
            imports = re.findall(import_pattern, content)

            # Ищем тестовые функции
            test_pattern = r"def\s+test_(\w+)"
            test_functions = re.findall(test_pattern, content)

            # Составляем список покрытых функций
            for module, items in imports:
                if not module.startswith("tests"):
                    for item in items.split(","):
                        item = item.strip()
                        if item:
                            covered_functions.append(f"{module}.{item}")

            # Также ищем в названиях тестов
            for test_func in test_functions:
                # test_order_manager_create -> OrderManager.create
                parts = test_func.split("_")
                if len(parts) >= 2:
                    class_name = "".join(p.capitalize() for p in parts[:-1])
                    method_name = parts[-1]
                    covered_functions.append(f"{class_name}.{method_name}")

        except Exception as e:
            print(f"⚠️ Ошибка анализа {test_file}: {e}")

        return covered_functions

    def generate_missing_tests(self, business_files: dict, existing_tests: dict) -> list[dict]:
        """Генерирует тесты для непокрытых функций"""
        missing_tests = []

        for file_path, functions in business_files.items():
            for func in functions:
                full_name = f"{file_path.replace('/', '.')}.{func}"

                if full_name not in existing_tests:
                    missing_tests.append(
                        {
                            "file": file_path,
                            "function": func,
                            "full_name": full_name,
                            "test_path": self.suggest_test_path(file_path, func),
                        }
                    )

        return missing_tests

    def suggest_test_path(self, source_file: str, function: str) -> str:
        """Предлагает путь для нового теста"""
        # trading/engine.py -> tests/unit/trading/test_engine.py
        parts = Path(source_file).parts

        if len(parts) > 1:
            category = parts[0]
            filename = Path(source_file).stem
            test_file = f"test_{filename}.py"
            return str(Path("tests") / "unit" / category / test_file)
        else:
            filename = Path(source_file).stem
            return str(Path("tests") / "unit" / f"test_{filename}.py")

    def update_existing_test(self, test_file: Path, new_scenarios: list[str]) -> bool:
        """Обновляет существующий тест новыми сценариями"""

        try:
            with open(test_file, encoding="utf-8") as f:
                content = f.read()

            # Добавляем новые тестовые сценарии в конец файла
            additional_tests = "\n\n# Автоматически добавленные тесты\n"

            for scenario in new_scenarios:
                if scenario not in content:
                    additional_tests += f"\n{scenario}\n"

            if len(additional_tests) > 50:  # Есть что добавить
                with open(test_file, "a", encoding="utf-8") as f:
                    f.write(additional_tests)
                return True

        except Exception as e:
            print(f"❌ Ошибка обновления {test_file}: {e}")

        return False

    def create_test_template(self, missing_test: dict) -> str:
        """Создаёт шаблон теста для отсутствующей функции"""

        func_name = missing_test["function"]
        file_path = missing_test["file"]

        # Определяем тип функции
        is_class_method = "." in func_name

        template = f'''"""
Автоматически сгенерированный тест для {file_path}
Функция: {func_name}
Сгенерировано: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# TODO: Проверить импорт
from {file_path.replace("/", ".").replace(".py", "")} import *


class Test{func_name.replace(".", "")}:
    """Тесты для {func_name}"""

    def test_{func_name.replace(".", "_")}_success(self):
        """Тест успешного выполнения"""
        # TODO: Реализовать тест
        assert True  # Заглушка

    def test_{func_name.replace(".", "_")}_with_invalid_input(self):
        """Тест с некорректными входными данными"""
        # TODO: Реализовать тест
        with pytest.raises(Exception):
            pass  # Заглушка

    def test_{func_name.replace(".", "_")}_edge_cases(self):
        """Тест граничных случаев"""
        # TODO: Реализовать тест
        assert True  # Заглушка

    @pytest.mark.asyncio
    async def test_{func_name.replace(".", "_")}_async(self):
        """Асинхронный тест (если функция async)"""
        # TODO: Проверить и реализовать если нужно
        pass

    def test_{func_name.replace(".", "_")}_performance(self):
        """Тест производительности"""
        import time
        start = time.time()
        # TODO: Вызов функции в цикле
        elapsed = time.time() - start
        assert elapsed < 1.0  # Должно выполняться быстро
'''

        return template

    def monitor_changes(self) -> dict[str, list[str]]:
        """Мониторит изменения в коде с последней проверки"""

        changes = {"modified": [], "new": [], "deleted": []}

        # Получаем хэши файлов из кэша
        old_hashes = self.coverage_data.get("file_hashes", {})
        new_hashes = {}

        for pattern in ["**/*.py"]:
            for file_path in self.project_root.glob(pattern):
                if "test" in str(file_path) or "__pycache__" in str(file_path):
                    continue

                rel_path = str(file_path.relative_to(self.project_root))

                # Вычисляем хэш файла
                with open(file_path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()

                new_hashes[rel_path] = file_hash

                if rel_path not in old_hashes:
                    changes["new"].append(rel_path)
                elif old_hashes[rel_path] != file_hash:
                    changes["modified"].append(rel_path)

        # Проверяем удалённые файлы
        for old_file in old_hashes:
            if old_file not in new_hashes:
                changes["deleted"].append(old_file)

        # Обновляем кэш
        self.coverage_data["file_hashes"] = new_hashes
        self.coverage_data["last_check"] = datetime.now().isoformat()

        return changes

    def run_coverage_report(self) -> dict:
        """Запускает отчёт о покрытии"""

        try:
            # Запускаем pytest с покрытием
            result = subprocess.run(
                ["pytest", "tests/", "--cov=.", "--cov-report=json", "--quiet"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            # Читаем результаты
            coverage_json = self.project_root / "coverage.json"
            if coverage_json.exists():
                with open(coverage_json) as f:
                    coverage = json.load(f)

                return {
                    "total_coverage": coverage.get("totals", {}).get("percent_covered", 0),
                    "files": coverage.get("files", {}),
                }

        except Exception as e:
            print(f"⚠️ Ошибка запуска покрытия: {e}")

        return {"total_coverage": 0, "files": {}}

    def generate_dashboard(self):
        """Генерирует дашборд с метриками тестирования"""

        dashboard_path = self.tests_dir / "test_dashboard.html"

        # Собираем метрики
        business_files = self.scan_project()
        existing_tests = self.find_existing_tests()
        missing_tests = self.generate_missing_tests(business_files, existing_tests)
        changes = self.monitor_changes()
        coverage = self.run_coverage_report()

        # Статистика
        total_functions = sum(len(funcs) for funcs in business_files.values())
        covered_functions = len(existing_tests)
        coverage_percent = (covered_functions / total_functions * 100) if total_functions > 0 else 0

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>BOT_AI_V3 Test Dashboard</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
        .metric {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric h3 {{ margin: 0; color: #7f8c8d; font-size: 14px; }}
        .metric .value {{ font-size: 32px; font-weight: bold; margin: 10px 0; }}
        .metric.good .value {{ color: #27ae60; }}
        .metric.warning .value {{ color: #f39c12; }}
        .metric.bad .value {{ color: #e74c3c; }}
        .section {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; }}
        .missing-test {{ padding: 8px; margin: 4px 0; background: #fee; border-left: 3px solid #e74c3c; }}
        .changed-file {{ padding: 8px; margin: 4px 0; background: #fef; border-left: 3px solid #f39c12; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ecf0f1; }}
        th {{ background: #34495e; color: white; }}
        .progress-bar {{ background: #ecf0f1; height: 20px; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ background: linear-gradient(90deg, #27ae60, #2ecc71); height: 100%; transition: width 0.3s; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 BOT_AI_V3 Test Dashboard</h1>
        <p>Последнее обновление: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="metrics">
        <div class="metric {"good" if coverage_percent > 80 else "warning" if coverage_percent > 60 else "bad"}">
            <h3>Покрытие функций</h3>
            <div class="value">{coverage_percent:.1f}%</div>
            <small>{covered_functions} из {total_functions}</small>
        </div>

        <div class="metric {"good" if coverage["total_coverage"] > 80 else "warning" if coverage["total_coverage"] > 60 else "bad"}">
            <h3>Покрытие кода</h3>
            <div class="value">{coverage["total_coverage"]:.1f}%</div>
            <small>По строкам кода</small>
        </div>

        <div class="metric {"bad" if len(missing_tests) > 20 else "warning" if len(missing_tests) > 10 else "good"}">
            <h3>Отсутствует тестов</h3>
            <div class="value">{len(missing_tests)}</div>
            <small>Функций без тестов</small>
        </div>

        <div class="metric {"warning" if len(changes["modified"]) > 0 else "good"}">
            <h3>Изменённых файлов</h3>
            <div class="value">{len(changes["modified"])}</div>
            <small>Требуют проверки тестов</small>
        </div>
    </div>

    <div class="section">
        <h2>📊 Покрытие по модулям</h2>
        <table>
            <tr>
                <th>Модуль</th>
                <th>Функций</th>
                <th>Покрыто</th>
                <th>Покрытие</th>
                <th>Прогресс</th>
            </tr>
"""

        # Группируем по модулям
        modules = {}
        for file_path, functions in business_files.items():
            module = file_path.split("/")[0] if "/" in file_path else "root"
            if module not in modules:
                modules[module] = {"total": 0, "covered": 0}
            modules[module]["total"] += len(functions)

            for func in functions:
                full_name = f"{file_path.replace('/', '.')}.{func}"
                if full_name in existing_tests:
                    modules[module]["covered"] += 1

        for module, stats in sorted(modules.items()):
            percent = (stats["covered"] / stats["total"] * 100) if stats["total"] > 0 else 0
            html += f"""
            <tr>
                <td><strong>{module}</strong></td>
                <td>{stats["total"]}</td>
                <td>{stats["covered"]}</td>
                <td>{percent:.1f}%</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {percent}%"></div>
                    </div>
                </td>
            </tr>
"""

        html += """
        </table>
    </div>

    <div class="section">
        <h2>⚠️ Требуют внимания</h2>
"""

        if changes["modified"]:
            html += "<h3>Изменённые файлы (проверьте тесты):</h3>"
            for file in changes["modified"][:10]:
                html += f'<div class="changed-file">📝 {file}</div>'

        if missing_tests:
            html += "<h3>Функции без тестов (топ-10):</h3>"
            for test in missing_tests[:10]:
                html += f'<div class="missing-test">❌ {test["file"]} → {test["function"]}</div>'

        html += """
    </div>

    <div class="section">
        <h2>🚀 Быстрые команды</h2>
        <pre>
# Сгенерировать отсутствующие тесты
python scripts/smart_test_manager.py generate

# Обновить существующие тесты
python scripts/smart_test_manager.py update

# Запустить все тесты
pytest tests/ -v

# Проверить покрытие
pytest tests/ --cov=. --cov-report=html
        </pre>
    </div>

    <script>
        // Автообновление каждые 30 секунд
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
"""

        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"📊 Дашборд создан: {dashboard_path}")

        # Сохраняем кэш
        self.save_cache()

        return {
            "total_functions": total_functions,
            "covered_functions": covered_functions,
            "missing_tests": len(missing_tests),
            "changed_files": len(changes["modified"]),
        }


@click.group()
def cli():
    """Умный менеджер тестов для BOT_AI_V3"""
    pass


@cli.command()
@click.option("--update", is_flag=True, help="Обновить существующие тесты")
def generate(update):
    """Генерирует недостающие тесты"""

    project_root = Path(__file__).parent.parent
    manager = SmartTestManager(project_root)

    print("🔍 Сканирование проекта...")
    business_files = manager.scan_project()
    existing_tests = manager.find_existing_tests()
    missing_tests = manager.generate_missing_tests(business_files, existing_tests)

    print(f"📊 Найдено {len(missing_tests)} функций без тестов")

    created_count = 0
    for missing in missing_tests[:20]:  # Создаём первые 20
        test_path = project_root / missing["test_path"]

        if not test_path.exists():
            test_path.parent.mkdir(parents=True, exist_ok=True)

            template = manager.create_test_template(missing)
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(template)

            print(f"✅ Создан тест: {missing['test_path']}")
            created_count += 1
        elif update:
            # Обновляем существующий тест
            if manager.update_existing_test(test_path, []):
                print(f"📝 Обновлён: {missing['test_path']}")

    print(f"\n✅ Создано {created_count} новых тестов")


@cli.command()
def dashboard():
    """Генерирует дашборд с метриками"""

    project_root = Path(__file__).parent.parent
    manager = SmartTestManager(project_root)

    print("📊 Генерация дашборда...")
    stats = manager.generate_dashboard()

    print(
        f"""
✅ Дашборд создан!

📈 Статистика:
  • Всего функций: {stats["total_functions"]}
  • Покрыто тестами: {stats["covered_functions"]}
  • Отсутствует тестов: {stats["missing_tests"]}
  • Изменено файлов: {stats["changed_files"]}

Откройте: tests/test_dashboard.html
"""
    )


@cli.command()
def monitor():
    """Мониторит изменения и предлагает обновить тесты"""

    project_root = Path(__file__).parent.parent
    manager = SmartTestManager(project_root)

    print("👀 Мониторинг изменений...")
    changes = manager.monitor_changes()

    if changes["modified"]:
        print(f"\n📝 Изменённые файлы ({len(changes['modified'])}):")
        for file in changes["modified"]:
            print(f"  • {file}")

        print("\n💡 Рекомендуется запустить тесты:")
        print("   pytest tests/ -v")

    if changes["new"]:
        print(f"\n🆕 Новые файлы ({len(changes['new'])}):")
        for file in changes["new"]:
            print(f"  • {file}")

        print("\n💡 Создайте тесты:")
        print("   python scripts/smart_test_manager.py generate")

    manager.save_cache()


@cli.command()
def coverage():
    """Показывает детальное покрытие"""

    project_root = Path(__file__).parent.parent
    manager = SmartTestManager(project_root)

    print("📊 Анализ покрытия...")
    coverage_data = manager.run_coverage_report()

    print(f"\n📈 Общее покрытие: {coverage_data['total_coverage']:.1f}%")

    # Топ непокрытых файлов
    if coverage_data["files"]:
        files_coverage = [
            (f, data.get("summary", {}).get("percent_covered", 0))
            for f, data in coverage_data["files"].items()
        ]
        files_coverage.sort(key=lambda x: x[1])

        print("\n❌ Файлы с низким покрытием:")
        for file, percent in files_coverage[:10]:
            if percent < 50:
                print(f"  • {file}: {percent:.1f}%")


if __name__ == "__main__":
    cli()
