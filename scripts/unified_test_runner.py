#!/usr/bin/env python3
"""
🚀 UNIFIED BOT_AI_V3 TEST RUNNER 🚀
Единая точка входа для всех систем тестирования

Объединяет:
- Enhanced Master Test Runner (новая система)
- Master Test Runner (legacy совместимость)
- Comprehensive Test Generator
- Performance & Coverage Analysis

Автор: Enhanced Testing System
Версия: 4.0.0
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent


class UnifiedTestRunner:
    """Единая система управления тестированием BOT_AI_V3"""

    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project_root = project_root
        self.results_dir = project_root / "analysis_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def print_banner(self):
        """Печатает баннер системы"""
        print(
            """
🚀            UNIFIED BOT_AI_V3 TEST RUNNER v4.0            🚀
════════════════════════════════════════════════════════════════
🎯 Единая точка входа для всех систем тестирования
🔍 Комплексный анализ кода и генерация тестов
⚡ Высокопроизводительный AST анализ (3775 функций)
🧠 ML-генерация тестов на основе паттернов
🔗 Анализ связей между классами (540 классов)
📊 Покрытие кода и мониторинг качества
════════════════════════════════════════════════════════════════
📁 Проект: {self.project_root}
📊 Результаты: {self.results_dir}
🌐 PostgreSQL: localhost:5555 (НЕ 5432!)
════════════════════════════════════════════════════════════════
"""
        )

    async def run_enhanced_analysis(self, mode: str = "full") -> dict[str, Any]:
        """Запускает улучшенную систему анализа"""
        print("🔥 Запуск Enhanced Master Test Runner...")

        cmd = [
            sys.executable,
            str(self.project_root / "scripts" / "enhanced_master_test_runner.py"),
            f"--mode={mode}",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=self.project_root,  # 10 минут
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "duration": "enhanced_system",
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "errors": "Enhanced analysis timeout (10 minutes)",
                "duration": 600,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": f"Enhanced analysis error: {e}",
                "duration": 0,
            }

    def run_comprehensive_test_generation(self) -> dict[str, Any]:
        """Запускает comprehensive test generator"""
        print("🧪 Запуск Comprehensive Test Generator...")

        cmd = [
            sys.executable,
            str(self.project_root / "scripts" / "comprehensive_test_generator.py"),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.project_root,  # 5 минут
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "tests_generated": True,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "errors": "Test generation timeout (5 minutes)",
                "tests_generated": False,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": f"Test generation error: {e}",
                "tests_generated": False,
            }

    def run_legacy_analysis(self, full_analysis: bool = False) -> dict[str, Any]:
        """Запускает legacy систему для совместимости"""
        print("🔄 Запуск Legacy Master Test Runner...")

        cmd = [sys.executable, str(self.project_root / "scripts" / "master_test_runner.py")]
        if full_analysis:
            cmd.append("--full-analysis")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                cwd=self.project_root,  # 10 минут
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "legacy_mode": True,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "errors": "Legacy analysis timeout (10 minutes)",
                "legacy_mode": True,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": f"Legacy analysis error: {e}",
                "legacy_mode": True,
            }

    def run_pytest_tests(self) -> dict[str, Any]:
        """Запускает pytest тесты"""
        print("🧪 Запуск pytest тестов...")

        cmd = [sys.executable, "-m", "pytest", "tests/", "--tb=short", "-v", "--disable-warnings"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.project_root,  # 5 минут
            )

            # Парсим вывод pytest для подсчета тестов
            output_lines = result.stdout.split("\n")
            tests_collected = 0
            tests_passed = 0
            tests_failed = 0

            for line in output_lines:
                if "collected" in line and "items" in line:
                    try:
                        tests_collected = int(line.split()[0])
                    except:
                        pass
                elif "passed" in line and "failed" in line:
                    # Парсим строку результатов
                    for part in line.split():
                        if "passed" in part:
                            try:
                                tests_passed = int(part.replace("passed", ""))
                            except:
                                pass
                        elif "failed" in part:
                            try:
                                tests_failed = int(part.replace("failed", ""))
                            except:
                                pass

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "tests_collected": tests_collected,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "coverage_run": False,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "errors": "Pytest timeout (5 minutes)",
                "tests_collected": 0,
                "tests_passed": 0,
                "tests_failed": 0,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": f"Pytest error: {e}",
                "tests_collected": 0,
                "tests_passed": 0,
                "tests_failed": 0,
            }

    def run_coverage_analysis(self) -> dict[str, Any]:
        """Запускает анализ покрытия кода"""
        print("📊 Запуск анализа покрытия...")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=.",
            "--cov-report=json",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--disable-warnings",
            "-q",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.project_root,  # 5 минут
            )

            # Читаем coverage.json если создался
            coverage_file = self.project_root / "coverage.json"
            coverage_data = {}

            if coverage_file.exists():
                try:
                    with open(coverage_file) as f:
                        coverage_data = json.load(f)
                except:
                    pass

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "coverage_data": coverage_data,
                "coverage_percentage": coverage_data.get("totals", {}).get("percent_covered", 0),
                "html_report": str(self.project_root / "htmlcov" / "index.html"),
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "errors": "Coverage analysis timeout (5 minutes)",
                "coverage_percentage": 0,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "errors": f"Coverage analysis error: {e}",
                "coverage_percentage": 0,
            }

    def generate_unified_report(self, results: dict[str, Any]) -> str:
        """Генерирует единый отчет"""
        print("📄 Генерация единого отчета...")

        # Сохраняем JSON отчет
        report_file = self.results_dir / "unified_test_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        # Генерируем Markdown отчет
        markdown_file = self.results_dir / "unified_test_report.md"
        markdown_content = self._generate_markdown_report(results)

        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return str(report_file)

    def _generate_markdown_report(self, results: dict[str, Any]) -> str:
        """Генерирует Markdown отчет"""
        report = f"""# 🚀 Unified BOT_AI_V3 Test Report

**Дата:** {time.strftime("%Y-%m-%d %H:%M:%S")}
**Проект:** BOT_AI_V3
**Версия системы тестирования:** 4.0.0

## 📊 Общие результаты

- **Общее время выполнения:** {results.get("total_duration", "N/A")}
- **Успешных этапов:** {results.get("successful_components", 0)}/{results.get("total_components", 0)}
- **Общая успешность:** {results.get("overall_success_rate", 0):.1f}%

## 🔥 Enhanced Analysis Results

- **Статус:** {"✅ Успешно" if results.get("enhanced_analysis", {}).get("success") else "❌ Ошибка"}
- **Файлов проанализировано:** {results.get("files_analyzed", 0)}
- **Функций найдено:** {results.get("functions_found", 0)}
- **Классов найдено:** {results.get("classes_found", 0)}

## 🧪 Test Generation Results

- **Статус:** {"✅ Успешно" if results.get("test_generation", {}).get("success") else "❌ Ошибка"}
- **Unit тестов создано:** {results.get("unit_tests_generated", 0)}
- **Integration тестов:** {results.get("integration_tests_generated", 0)}
- **Performance тестов:** {results.get("performance_tests_generated", 0)}

## 📊 Coverage Analysis

- **Покрытие:** {results.get("coverage_analysis", {}).get("coverage_percentage", 0):.1f}%
- **Тестов собрано:** {results.get("pytest_results", {}).get("tests_collected", 0)}
- **Тестов прошло:** {results.get("pytest_results", {}).get("tests_passed", 0)}
- **Тестов упало:** {results.get("pytest_results", {}).get("tests_failed", 0)}

## 🔍 Detailed Results

### Enhanced Analysis
```
{results.get("enhanced_analysis", {}).get("output", "No output")[:500]}...
```

### Test Generation
```
{results.get("test_generation", {}).get("output", "No output")[:500]}...
```

### Coverage Analysis
```
{results.get("coverage_analysis", {}).get("output", "No output")[:500]}...
```

## 📂 Generated Files

- **JSON отчет:** `analysis_results/unified_test_report.json`
- **HTML дашборд:** `analysis_results/enhanced_testing_dashboard.html`
- **Coverage HTML:** `htmlcov/index.html`
- **Enhanced results:** `analysis_results/enhanced_*.json`

## 🚀 Quick Commands

```bash
# Повторный запуск полного анализа
python3 scripts/unified_test_runner.py --mode=full

# Только генерация тестов
python3 scripts/unified_test_runner.py --mode=generate

# Только анализ покрытия
python3 scripts/unified_test_runner.py --mode=coverage

# Legacy система
python3 scripts/unified_test_runner.py --mode=legacy
```

## 🎯 Recommendations

"""

        # Добавляем рекомендации на основе результатов
        if results.get("coverage_analysis", {}).get("coverage_percentage", 0) < 50:
            report += (
                "- 🔴 **Критично:** Покрытие кода слишком низкое. Запустите генерацию тестов.\n"
            )

        if results.get("pytest_results", {}).get("tests_failed", 0) > 0:
            report += "- ⚠️ **Внимание:** Есть падающие тесты. Необходимо исправление.\n"

        if not results.get("enhanced_analysis", {}).get("success"):
            report += "- 🔧 **Исправить:** Проблемы с enhanced анализом. Проверьте логи.\n"

        report += f"\n---\n**Отчет сгенерирован:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n"

        return report

    async def run_unified_analysis(self, mode: str = "full") -> dict[str, Any]:
        """Запускает единую систему анализа"""
        start_time = time.time()

        self.print_banner()

        results = {"start_time": start_time, "mode": mode, "version": "4.0.0"}

        components_run = 0
        components_successful = 0

        try:
            if mode in ["full", "enhanced"]:
                # Enhanced анализ
                enhanced_result = await self.run_enhanced_analysis("full")
                results["enhanced_analysis"] = enhanced_result
                components_run += 1
                if enhanced_result["success"]:
                    components_successful += 1

            if mode in ["full", "generate"]:
                # Генерация тестов
                test_gen_result = self.run_comprehensive_test_generation()
                results["test_generation"] = test_gen_result
                components_run += 1
                if test_gen_result["success"]:
                    components_successful += 1

            if mode in ["full", "tests", "pytest"]:
                # Pytest тесты
                pytest_result = self.run_pytest_tests()
                results["pytest_results"] = pytest_result
                components_run += 1
                if pytest_result["success"]:
                    components_successful += 1

            if mode in ["full", "coverage"]:
                # Анализ покрытия
                coverage_result = self.run_coverage_analysis()
                results["coverage_analysis"] = coverage_result
                components_run += 1
                if coverage_result["success"]:
                    components_successful += 1

            if mode == "legacy":
                # Legacy система
                legacy_result = self.run_legacy_analysis(full_analysis=True)
                results["legacy_analysis"] = legacy_result
                components_run += 1
                if legacy_result["success"]:
                    components_successful += 1

        except Exception as e:
            results["global_error"] = str(e)
            print(f"❌ Глобальная ошибка: {e}")

        # Финальная статистика
        total_duration = time.time() - start_time
        results.update(
            {
                "total_duration": total_duration,
                "total_components": components_run,
                "successful_components": components_successful,
                "overall_success_rate": (
                    (components_successful / components_run * 100) if components_run > 0 else 0
                ),
                "end_time": time.time(),
            }
        )

        # Генерируем отчет
        report_file = self.generate_unified_report(results)

        # Финальный вывод
        print(
            f"""
🎉            UNIFIED TEST RUNNER - ФИНАЛЬНЫЙ ОТЧЁТ            🎉
════════════════════════════════════════════════════════════════
⏱️  Общее время выполнения: {total_duration:.1f}с
✅ Успешных компонентов: {components_successful}/{components_run}
📊 Общая успешность: {results["overall_success_rate"]:.1f}%
🚀 Режим выполнения: {mode}
════════════════════════════════════════════════════════════════
🏆 UNIFIED СИСТЕМА ТЕСТИРОВАНИЯ ЗАВЕРШЕНА!

📂 РЕЗУЛЬТАТЫ:
────────────────────────────────────────
📄 Единый отчёт: {report_file}
📝 Markdown отчёт: {self.results_dir}/unified_test_report.md
🌐 Дашборд: {self.results_dir}/enhanced_testing_dashboard.html
📊 Coverage: htmlcov/index.html

🚀 БЫСТРЫЕ КОМАНДЫ:
────────────────────────────────────────
# Полный анализ
python3 scripts/unified_test_runner.py --mode=full

# Только тесты
python3 scripts/unified_test_runner.py --mode=tests

# Только покрытие
python3 scripts/unified_test_runner.py --mode=coverage

# Enhanced анализ
python3 scripts/unified_test_runner.py --mode=enhanced

🎯 СТАТУС: {"🟢 ВСЁ ОТЛИЧНО!" if results["overall_success_rate"] >= 80 else "🟡 ТРЕБУЕТ ВНИМАНИЯ" if results["overall_success_rate"] >= 50 else "🔴 НУЖНЫ ИСПРАВЛЕНИЯ"}
════════════════════════════════════════════════════════════════
"""
        )

        return results


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="🚀 Unified BOT_AI_V3 Test Runner v4.0 - Единая точка входа для всех систем тестирования",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Доступные режимы:
  full        - Полный анализ (enhanced + генерация + тесты + покрытие)
  enhanced    - Только enhanced анализ AST и ML генерация
  generate    - Только генерация новых тестов
  tests       - Только запуск pytest тестов
  coverage    - Только анализ покрытия кода
  legacy      - Legacy master test runner (совместимость)

Примеры использования:
  python3 scripts/unified_test_runner.py --mode=full
  python3 scripts/unified_test_runner.py --mode=coverage
  python3 scripts/unified_test_runner.py --mode=legacy
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["full", "enhanced", "generate", "tests", "coverage", "legacy"],
        default="full",
        help="Режим выполнения (по умолчанию: full)",
    )

    parser.add_argument(
        "--project-root", type=Path, default=PROJECT_ROOT, help="Корневая папка проекта"
    )

    args = parser.parse_args()

    # Создаем и запускаем runner
    runner = UnifiedTestRunner(args.project_root)

    try:
        results = asyncio.run(runner.run_unified_analysis(args.mode))

        # Возвращаем код выхода в зависимости от успешности
        if results["overall_success_rate"] >= 80:
            sys.exit(0)  # Успех
        elif results["overall_success_rate"] >= 50:
            sys.exit(1)  # Частичный успех
        else:
            sys.exit(2)  # Много ошибок

    except KeyboardInterrupt:
        print("\n❌ Выполнение прервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
