#!/usr/bin/env python3
"""
Быстрый запуск тестов с моментальным обнаружением проблем
Запускает только изменённые модули и связанные тесты
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import click


class QuickTestRunner:
    """Быстрый запуск релевантных тестов"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.failed_tests = []
        self.slow_tests = []

    def get_changed_files(self) -> list[str]:
        """Получает список изменённых файлов"""
        try:
            # Изменения относительно main
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD", "origin/main"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]
        except:
            pass

        # Если git не работает, проверяем последние изменённые файлы
        import os
        import time

        now = time.time()
        recent_files = []

        for file_path in self.project_root.rglob("*.py"):
            if "test" not in str(file_path) and "__pycache__" not in str(file_path):
                mtime = os.path.getmtime(file_path)
                if now - mtime < 3600:  # Изменены в последний час
                    recent_files.append(str(file_path.relative_to(self.project_root)))

        return recent_files

    def find_related_tests(self, changed_file: str) -> list[str]:
        """Находит тесты связанные с изменённым файлом"""

        tests = []

        # trading/engine.py -> tests/unit/trading/test_engine.py
        if "/" in changed_file:
            parts = Path(changed_file).parts
            category = parts[0]
            module = Path(changed_file).stem

            test_patterns = [
                f"tests/unit/{category}/test_{module}.py",
                f"tests/unit/{category}/test_{module}_*.py",
                f"tests/integration/test_{module}.py",
                f"tests/integration/test_{category}_{module}.py",
            ]

            for pattern in test_patterns:
                for test_file in self.project_root.glob(pattern):
                    if test_file.exists():
                        tests.append(str(test_file))

        return tests

    def run_test(self, test_file: str) -> dict:
        """Запускает один тест и возвращает результат"""

        start_time = time.time()

        result = subprocess.run(
            ["pytest", test_file, "-v", "--tb=short", "--quiet"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )

        elapsed = time.time() - start_time

        return {
            "file": test_file,
            "passed": result.returncode == 0,
            "time": elapsed,
            "output": result.stdout if not result.returncode == 0 else "",
            "errors": result.stderr,
        }

    def run_quick_tests(self, changed_files: list[str]) -> dict:
        """Запускает быстрые тесты для изменённых файлов"""

        all_tests = set()

        # Находим все связанные тесты
        for file in changed_files:
            tests = self.find_related_tests(file)
            all_tests.update(tests)

        if not all_tests:
            return {"status": "no_tests", "files": changed_files}

        print(f"🧪 Запуск {len(all_tests)} тестов...")

        results = {"total": len(all_tests), "passed": 0, "failed": 0, "slow": 0, "details": []}

        for test in all_tests:
            test_name = Path(test).name
            print(f"  • {test_name}...", end=" ")

            result = self.run_test(test)

            if result["passed"]:
                results["passed"] += 1
                if result["time"] > 1.0:
                    print(f"✅ (медленно: {result['time']:.2f}s)")
                    results["slow"] += 1
                    self.slow_tests.append(test)
                else:
                    print(f"✅ ({result['time']:.2f}s)")
            else:
                results["failed"] += 1
                print("❌ FAILED!")
                self.failed_tests.append(test)
                results["details"].append(result)

        return results

    def run_smoke_tests(self) -> bool:
        """Запускает критические smoke тесты"""

        smoke_tests = [
            "tests/unit/trading/test_engine.py::test_engine_initialization",
            "tests/unit/database/test_connections.py::test_db_connection",
            "tests/unit/ml/test_ml_manager.py::test_model_loading",
        ]

        print("🔥 Smoke тесты...")

        for test in smoke_tests:
            if "::" in test:
                file, func = test.split("::")
                if Path(self.project_root / file).exists():
                    result = subprocess.run(
                        ["pytest", file, "-k", func, "-q"],
                        capture_output=True,
                        cwd=self.project_root,
                    )

                    if result.returncode != 0:
                        print(f"  ❌ {func} - КРИТИЧЕСКАЯ ОШИБКА!")
                        return False

        print("  ✅ Все критические компоненты работают")
        return True

    def check_imports(self, file_path: str) -> bool:
        """Проверяет что все импорты работают"""

        try:
            # Пытаемся импортировать модуль
            spec = __import__(file_path.replace("/", ".").replace(".py", ""))
            return True
        except ImportError as e:
            print(f"  ❌ Import error: {e}")
            return False
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return False

    def generate_report(self, results: dict) -> str:
        """Генерирует отчёт о тестировании"""

        report = f"""
# 🧪 Отчёт быстрого тестирования
Время: {datetime.now().strftime('%H:%M:%S')}

## 📊 Результаты:
- Всего тестов: {results.get('total', 0)}
- ✅ Прошло: {results.get('passed', 0)}
- ❌ Провалено: {results.get('failed', 0)}
- 🐌 Медленных: {results.get('slow', 0)}
"""

        if self.failed_tests:
            report += "\n## ❌ Провалившиеся тесты:\n"
            for test in self.failed_tests:
                report += f"- {test}\n"

            report += "\n## 🔍 Детали ошибок:\n"
            for detail in results.get("details", []):
                if not detail["passed"]:
                    report += f"\n### {detail['file']}\n"
                    report += "```\n"
                    report += detail["output"][:500]  # Первые 500 символов
                    report += "\n```\n"

        if self.slow_tests:
            report += "\n## 🐌 Медленные тесты (>1s):\n"
            for test in self.slow_tests:
                report += f"- {test}\n"

        return report


@click.command()
@click.option("--watch", is_flag=True, help="Режим наблюдения")
@click.option("--smoke", is_flag=True, help="Только smoke тесты")
@click.option("--all", is_flag=True, help="Все тесты")
def main(watch, smoke, all):
    """Быстрый запуск тестов с обнаружением проблем"""

    runner = QuickTestRunner()

    if smoke:
        print("🔥 Запуск smoke тестов...")
        if runner.run_smoke_tests():
            print("✅ Система работает!")
        else:
            print("❌ Критические проблемы!")
            sys.exit(1)
        return

    if all:
        print("🧪 Запуск всех тестов...")
        result = subprocess.run(["pytest", "tests/", "-q", "--tb=short"], cwd=runner.project_root)
        sys.exit(result.returncode)

    if watch:
        print("👀 Режим наблюдения за изменениями...")
        last_check = {}

        while True:
            try:
                changed = runner.get_changed_files()

                # Проверяем только новые изменения
                new_changes = [f for f in changed if f not in last_check]

                if new_changes:
                    print(f"\n🔄 Обнаружены изменения: {len(new_changes)} файлов")
                    results = runner.run_quick_tests(new_changes)

                    if results.get("failed", 0) > 0:
                        print("\n❌ ТЕСТЫ ПРОВАЛЕНЫ!")
                        print(runner.generate_report(results))
                    else:
                        print("\n✅ Все тесты прошли!")

                    last_check = dict.fromkeys(changed, True)

                time.sleep(5)  # Проверка каждые 5 секунд

            except KeyboardInterrupt:
                print("\n👋 Остановка наблюдения")
                break

    else:
        # Обычный запуск
        print("🔍 Поиск изменённых файлов...")
        changed = runner.get_changed_files()

        if not changed:
            print("✅ Изменений не обнаружено")

            # Запускаем smoke тесты на всякий случай
            if runner.run_smoke_tests():
                print("✅ Smoke тесты пройдены")
            return

        print(f"📝 Изменено файлов: {len(changed)}")
        for file in changed[:5]:
            print(f"  • {file}")

        if len(changed) > 5:
            print(f"  ... и ещё {len(changed) - 5}")

        # Запускаем тесты
        results = runner.run_quick_tests(changed)

        # Генерируем отчёт
        report = runner.generate_report(results)

        # Сохраняем отчёт
        report_path = runner.project_root / "tests" / "last_test_run.md"
        with open(report_path, "w") as f:
            f.write(report)

        print(report)

        if results.get("failed", 0) > 0:
            print(f"\n💡 Для детального анализа: cat {report_path}")
            sys.exit(1)
        else:
            print("\n✅ Все тесты прошли успешно!")


if __name__ == "__main__":
    main()
