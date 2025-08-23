#!/usr/bin/env python3
"""
Комплексный тестовый набор для Enhanced Position Tracker
Объединяет все типы тестов в единый интерфейс
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.logger import setup_logger

logger = setup_logger(__name__)


class PositionTrackerTestSuite:
    """
    Главный класс для запуска всех тестов Position Tracker
    """

    def __init__(self):
        self.test_results: dict[str, Any] = {}
        self.test_modules = {
            "unit": "tests/unit/test_position_tracker.py",
            "integration": "tests/integration/test_position_tracker_integration.py",
            "performance": "tests/performance/test_position_tracker_performance.py",
        }

    async def run_all_tests(self, verbose: bool = False) -> dict[str, Any]:
        """
        Запускает все тесты Position Tracker

        Args:
            verbose: Подробный вывод

        Returns:
            Результаты всех тестов
        """
        logger.info("🚀 Запуск полного набора тестов Enhanced Position Tracker")

        overall_start_time = time.perf_counter()

        # Запускаем каждый тип тестов
        for test_type, test_module in self.test_modules.items():
            logger.info(f"📋 Запуск {test_type} тестов...")

            result = await self._run_test_module(test_type, test_module, verbose)
            self.test_results[test_type] = result

            if result["success"]:
                logger.info(f"✅ {test_type} тесты завершены успешно")
            else:
                logger.error(f"❌ {test_type} тесты завершились с ошибками")

        overall_time = time.perf_counter() - overall_start_time

        # Генерируем общий отчет
        summary = self._generate_summary(overall_time)
        self.test_results["summary"] = summary

        return self.test_results

    async def run_unit_tests(self, verbose: bool = False) -> dict[str, Any]:
        """Запуск только unit тестов"""
        logger.info("🔧 Запуск Unit тестов Position Tracker")
        return await self._run_test_module("unit", self.test_modules["unit"], verbose)

    async def run_integration_tests(self, verbose: bool = False) -> dict[str, Any]:
        """Запуск только integration тестов"""
        logger.info("🔗 Запуск Integration тестов Position Tracker")
        return await self._run_test_module("integration", self.test_modules["integration"], verbose)

    async def run_performance_tests(self, verbose: bool = False) -> dict[str, Any]:
        """Запуск только performance тестов"""
        logger.info("⚡ Запуск Performance тестов Position Tracker")
        return await self._run_test_module("performance", self.test_modules["performance"], verbose)

    async def _run_test_module(
        self, test_type: str, module_path: str, verbose: bool
    ) -> dict[str, Any]:
        """
        Запускает конкретный модуль тестов

        Args:
            test_type: Тип тестов
            module_path: Путь к модулю
            verbose: Подробный вывод

        Returns:
            Результат выполнения тестов
        """
        start_time = time.perf_counter()

        try:
            # Формируем команду pytest
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(project_root / module_path),
                "-v" if verbose else "-q",
                "--tb=short",
                "--json-report",
                f"--json-report-file=test_results/position_tracker_{test_type}_report.json",
                "--maxfail=10",  # Останавливаемся после 10 ошибок
            ]

            # Запускаем тесты
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300  # 5 минут на каждый тип тестов
            )

            end_time = time.perf_counter()
            execution_time = end_time - start_time

            # Парсим результаты
            test_result = {
                "success": result.returncode == 0,
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_type": test_type,
            }

            # Извлекаем статистику из вывода pytest
            test_result.update(self._parse_pytest_output(result.stdout))

            return test_result

        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Таймаут при выполнении {test_type} тестов")
            return {
                "success": False,
                "execution_time": 300,
                "error": "Timeout",
                "test_type": test_type,
            }
        except Exception as e:
            logger.error(f"💥 Ошибка при выполнении {test_type} тестов: {e}")
            return {
                "success": False,
                "execution_time": time.perf_counter() - start_time,
                "error": str(e),
                "test_type": test_type,
            }

    def _parse_pytest_output(self, output: str) -> dict[str, Any]:
        """
        Парсит вывод pytest для извлечения статистики

        Args:
            output: Вывод pytest

        Returns:
            Статистика тестов
        """
        stats = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "total": 0}

        # Ищем строку с результатами
        lines = output.split("\n")
        for line in lines:
            if "passed" in line or "failed" in line:
                # Примеры: "5 passed", "2 failed, 3 passed", etc.
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.isdigit() and i + 1 < len(parts):
                        count = int(part)
                        status = parts[i + 1].replace(",", "").lower()

                        if status in stats:
                            stats[status] = count

        stats["total"] = sum([stats["passed"], stats["failed"], stats["skipped"], stats["errors"]])

        return stats

    def _generate_summary(self, total_time: float) -> dict[str, Any]:
        """
        Генерирует общий отчет по всем тестам

        Args:
            total_time: Общее время выполнения

        Returns:
            Сводный отчет
        """
        summary = {
            "total_execution_time": total_time,
            "overall_success": True,
            "test_types_run": len(self.test_results),
            "total_tests": 0,
            "total_passed": 0,
            "total_failed": 0,
            "total_skipped": 0,
            "total_errors": 0,
            "success_rate": 0.0,
            "performance_metrics": {},
        }

        # Агрегируем результаты
        for test_type, result in self.test_results.items():
            if test_type == "summary":
                continue

            if not result.get("success", False):
                summary["overall_success"] = False

            # Суммируем статистику
            for key in ["total", "passed", "failed", "skipped", "errors"]:
                if key in result:
                    summary[f"total_{key}"] += result[key]

            # Добавляем метрики производительности
            if test_type == "performance":
                summary["performance_metrics"]["execution_time"] = result.get("execution_time", 0)
                summary["performance_metrics"]["performance_tests"] = result.get("total", 0)

        # Рассчитываем процент успешности
        if summary["total_total"] > 0:
            summary["success_rate"] = (summary["total_passed"] / summary["total_total"]) * 100

        return summary

    def print_summary(self):
        """Выводит краткий отчет о результатах тестирования"""
        if "summary" not in self.test_results:
            logger.warning("Нет данных для отчета")
            return

        summary = self.test_results["summary"]

        print("\n" + "=" * 80)
        print("🎯 ENHANCED POSITION TRACKER TEST RESULTS")
        print("=" * 80)

        # Общая информация
        print(f"📊 Общее время выполнения: {summary['total_execution_time']:.2f}s")
        print(f"🏆 Общий результат: {'✅ УСПЕХ' if summary['overall_success'] else '❌ НЕУДАЧА'}")
        print(f"📈 Процент успешности: {summary['success_rate']:.1f}%")

        # Детализация по типам тестов
        print("\n📋 Статистика по типам тестов:")
        for test_type in ["unit", "integration", "performance"]:
            if test_type in self.test_results:
                result = self.test_results[test_type]
                status = "✅" if result.get("success", False) else "❌"
                time_taken = result.get("execution_time", 0)
                total_tests = result.get("total", 0)
                passed_tests = result.get("passed", 0)

                print(
                    f"  {status} {test_type.capitalize()}: {passed_tests}/{total_tests} ({time_taken:.2f}s)"
                )

        # Общая статистика
        print("\n🔢 Общая статистика:")
        print(f"  📝 Всего тестов: {summary['total_total']}")
        print(f"  ✅ Пройдено: {summary['total_passed']}")
        print(f"  ❌ Провалено: {summary['total_failed']}")
        print(f"  ⏭️ Пропущено: {summary['total_skipped']}")
        print(f"  💥 Ошибок: {summary['total_errors']}")

        # Performance метрики
        if summary["performance_metrics"]:
            perf = summary["performance_metrics"]
            print("\n⚡ Performance метрики:")
            print(f"  🚀 Performance тесты: {perf.get('performance_tests', 0)}")
            print(f"  ⏱️ Время выполнения: {perf.get('execution_time', 0):.2f}s")

        # Рекомендации
        print("\n💡 Рекомендации:")
        if summary["overall_success"]:
            print("  🎉 Все тесты Position Tracker прошли успешно!")
            print("  ✨ Система готова к использованию")
        else:
            print("  🔍 Проверьте детальные логи для анализа ошибок")
            print("  🛠️ Исправьте найденные проблемы перед продакшеном")

        print("=" * 80)

    async def generate_html_report(
        self, output_file: str = "test_results/position_tracker_report.html"
    ):
        """
        Генерирует HTML отчет по тестам

        Args:
            output_file: Путь к выходному HTML файлу
        """
        if not self.test_results:
            logger.warning("Нет данных для генерации отчета")
            return

        html_content = self._create_html_report()

        # Создаем директорию если не существует
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"📄 HTML отчет сохранен: {output_file}")

    def _create_html_report(self) -> str:
        """Создает HTML контент для отчета"""
        summary = self.test_results.get("summary", {})

        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Position Tracker Test Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 20px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ color: #2c3e50; margin: 0; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .card.success {{ background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%); }}
        .card.danger {{ background: linear-gradient(135deg, #f44336 0%, #da190b 100%); }}
        .card h3 {{ margin: 0 0 10px 0; font-size: 2em; }}
        .card p {{ margin: 0; opacity: 0.9; }}
        .test-section {{ margin-bottom: 30px; }}
        .test-section h2 {{ color: #2c3e50; border-left: 4px solid #3498db; padding-left: 15px; }}
        .test-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
        .test-item {{ border: 1px solid #ddd; border-radius: 6px; padding: 15px; }}
        .test-item.success {{ border-left: 4px solid #4CAF50; }}
        .test-item.failure {{ border-left: 4px solid #f44336; }}
        .test-item h4 {{ margin: 0 0 10px 0; color: #333; }}
        .test-item .stats {{ font-size: 0.9em; color: #666; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Enhanced Position Tracker</h1>
            <h2>Test Results Report</h2>
            <p>Сгенерирован: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="card {'success' if summary.get('overall_success') else 'danger'}">
                <h3>{'✅' if summary.get('overall_success') else '❌'}</h3>
                <p>Общий результат</p>
            </div>
            <div class="card">
                <h3>{summary.get('success_rate', 0):.1f}%</h3>
                <p>Процент успешности</p>
            </div>
            <div class="card">
                <h3>{summary.get('total_total', 0)}</h3>
                <p>Всего тестов</p>
            </div>
            <div class="card">
                <h3>{summary.get('total_execution_time', 0):.1f}s</h3>
                <p>Время выполнения</p>
            </div>
        </div>
        
        <div class="test-section">
            <h2>📋 Результаты по типам тестов</h2>
            <div class="test-grid">
        """

        # Добавляем карточки для каждого типа тестов
        for test_type in ["unit", "integration", "performance"]:
            if test_type in self.test_results:
                result = self.test_results[test_type]
                success = result.get("success", False)

                html += f"""
                <div class="test-item {'success' if success else 'failure'}">
                    <h4>{'✅' if success else '❌'} {test_type.capitalize()} Tests</h4>
                    <div class="stats">
                        <p><strong>Время:</strong> {result.get('execution_time', 0):.2f}s</p>
                        <p><strong>Пройдено:</strong> {result.get('passed', 0)}/{result.get('total', 0)}</p>
                        <p><strong>Провалено:</strong> {result.get('failed', 0)}</p>
                        <p><strong>Пропущено:</strong> {result.get('skipped', 0)}</p>
                    </div>
                </div>
                """

        html += """
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 Автоматически сгенерированный отчет Enhanced Position Tracker Test Suite</p>
        </div>
    </div>
</body>
</html>
        """

        return html


async def main():
    """Главная функция для запуска тестов"""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced Position Tracker Test Suite")
    parser.add_argument(
        "--type",
        choices=["all", "unit", "integration", "performance"],
        default="all",
        help="Тип тестов для запуска",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    parser.add_argument("--html-report", action="store_true", help="Генерировать HTML отчет")

    args = parser.parse_args()

    suite = PositionTrackerTestSuite()

    # Запускаем тесты
    if args.type == "all":
        await suite.run_all_tests(verbose=args.verbose)
    elif args.type == "unit":
        result = await suite.run_unit_tests(verbose=args.verbose)
        suite.test_results = {"unit": result}
    elif args.type == "integration":
        result = await suite.run_integration_tests(verbose=args.verbose)
        suite.test_results = {"integration": result}
    elif args.type == "performance":
        result = await suite.run_performance_tests(verbose=args.verbose)
        suite.test_results = {"performance": result}

    # Выводим отчет
    suite.print_summary()

    # Генерируем HTML отчет если запрошено
    if args.html_report:
        await suite.generate_html_report()

    # Возвращаем код завершения
    overall_success = suite.test_results.get("summary", {}).get("overall_success", False)
    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    asyncio.run(main())
