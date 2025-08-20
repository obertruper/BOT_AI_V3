#!/usr/bin/env python3
"""
Централизованный запуск тестов BOT_AI_V3 с поддержкой цепочек и детальной отчетностью
"""

import argparse
import subprocess
import time


class Colors:
    """ANSI цвета для вывода"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class TestRunner:
    """Централизованный runner для тестов"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.test_suites = {
            "unit": {
                "path": "tests/unit",
                "markers": "-m unit",
                "timeout": 300,
                "description": "Unit тесты для отдельных компонентов",
            },
            "ml": {
                "path": "tests/unit/ml",
                "markers": "-m ml",
                "timeout": 600,
                "description": "Тесты Machine Learning компонентов",
            },
            "database": {
                "path": "tests/unit/database",
                "markers": "-m 'unit and not slow'",
                "timeout": 300,
                "description": "Тесты базы данных",
            },
            "integration": {
                "path": "tests/integration",
                "markers": "-m integration",
                "timeout": 900,
                "description": "Интеграционные тесты",
            },
            "performance": {
                "path": "tests/performance",
                "markers": "-m performance",
                "timeout": 1200,
                "description": "Performance и load тесты",
            },
            "smoke": {
                "path": "tests",
                "markers": "-m smoke",
                "timeout": 180,
                "description": "Быстрые smoke тесты",
            },
            # === DYNAMIC SL/TP TEST SUITES ===
            "dynamic_sltp_unit": {
                "path": "tests/unit/trading/orders/test_dynamic_sltp_calculator.py",
                "markers": "-m 'unit and sltp'",
                "timeout": 300,
                "description": "Dynamic SL/TP unit тесты",
            },
            "dynamic_sltp_integration": {
                "path": "tests/integration/test_dynamic_sltp_integration.py",
                "markers": "-m 'integration and sltp'",
                "timeout": 600,
                "description": "Dynamic SL/TP интеграционные тесты",
            },
            "dynamic_sltp_e2e": {
                "path": "tests/integration/test_dynamic_sltp_e2e.py",
                "markers": "-m 'e2e and sltp'",
                "timeout": 900,
                "description": "Dynamic SL/TP end-to-end тесты",
            },
            "dynamic_sltp_performance": {
                "path": "tests/performance/test_dynamic_sltp_performance.py",
                "markers": "-m 'performance and sltp'",
                "timeout": 1200,
                "description": "Dynamic SL/TP performance тесты",
            },
            "dynamic_sltp_all": {
                "path": "tests/unit/trading/orders/test_dynamic_sltp_calculator.py tests/integration/test_dynamic_sltp_integration.py tests/integration/test_dynamic_sltp_e2e.py",
                "markers": "-m sltp",
                "timeout": 1500,
                "description": "Полный набор Dynamic SL/TP тестов",
            },
        }

        # Предопределенные цепочки
        self.chains = {
            "quick": ["smoke", "unit"],
            "standard": ["unit", "ml", "database"],
            "full": ["unit", "ml", "database", "integration", "performance"],
            "ml-focus": ["ml", "database", "integration"],
            "ci": ["smoke", "unit", "ml"],
            # Dynamic SL/TP chains
            "dynamic_sltp_quick": ["dynamic_sltp_unit", "dynamic_sltp_integration"],
            "dynamic_sltp_complete": ["dynamic_sltp_unit", "dynamic_sltp_integration", "dynamic_sltp_e2e"],
            "dynamic_sltp_full": ["dynamic_sltp_unit", "dynamic_sltp_integration", "dynamic_sltp_e2e", "dynamic_sltp_performance"],
        }

    def print_header(self, text: str):
        """Вывод заголовка"""
        print(f"\n{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")

    def print_suite_info(self, suite_name: str):
        """Вывод информации о наборе тестов"""
        suite = self.test_suites[suite_name]
        print(f"{Colors.OKBLUE}📦 Набор тестов:{Colors.ENDC} {suite_name}")
        print(f"{Colors.OKBLUE}📄 Описание:{Colors.ENDC} {suite['description']}")
        print(f"{Colors.OKBLUE}📁 Путь:{Colors.ENDC} {suite['path']}")
        print(f"{Colors.OKBLUE}🏷️  Маркеры:{Colors.ENDC} {suite['markers']}")
        print(f"{Colors.OKBLUE}⏱️  Таймаут:{Colors.ENDC} {suite['timeout']}s\n")

    def run_suite(self, suite_name: str, extra_args: list[str] = None) -> tuple[bool, float, dict]:
        """Запуск конкретного набора тестов"""
        if suite_name not in self.test_suites:
            print(f"{Colors.FAIL}❌ Неизвестный набор тестов: {suite_name}{Colors.ENDC}")
            return False, 0.0, {}

        suite = self.test_suites[suite_name]

        # Формируем команду
        cmd = [
            "pytest",
            suite["path"],
            suite["markers"],
            "-v" if self.verbose else "-q",
            "--tb=short",
        ]

        # Добавляем дополнительные аргументы
        if extra_args:
            cmd.extend(extra_args)

        # Запускаем тесты
        start_time = time.time()

        if self.verbose:
            print(f"{Colors.OKCYAN}🚀 Запуск команды:{Colors.ENDC} {' '.join(cmd)}\n")

        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time

        # Парсим результаты
        success = result.returncode == 0
        stats = self._parse_test_results(suite_name)

        # Выводим результаты
        if success:
            print(f"\n{Colors.OKGREEN}✅ {suite_name} тесты пройдены успешно!{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}❌ {suite_name} тесты провалены!{Colors.ENDC}")
            if result.stderr:
                print(f"{Colors.WARNING}Ошибки:{Colors.ENDC}\n{result.stderr}")

        return success, duration, stats

    def _parse_test_results(self, suite_name: str) -> dict:
        """Парсинг результатов из вывода pytest"""
        # Пока возвращаем пустую статистику
        # В будущем можно парсить stdout
        stats = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}

        return stats

    def run_chain(self, chain: list[str], stop_on_failure: bool = True) -> dict:
        """Запуск цепочки тестов"""
        results = {}
        total_start = time.time()

        self.print_header(f"Запуск цепочки тестов: {' → '.join(chain)}")

        for i, suite in enumerate(chain, 1):
            print(f"\n{Colors.BOLD}[{i}/{len(chain)}] Запуск {suite} тестов{Colors.ENDC}")
            print("-" * 60)

            self.print_suite_info(suite)

            success, duration, stats = self.run_suite(suite)

            results[suite] = {"success": success, "duration": duration, "stats": stats}

            # Выводим статистику
            self._print_suite_stats(suite, stats, duration)

            if not success and stop_on_failure:
                print(f"\n{Colors.FAIL}⛔ Остановка цепочки из-за ошибки в {suite}{Colors.ENDC}")
                break

        total_duration = time.time() - total_start
        self._print_final_report(results, total_duration)

        return results

    def _print_suite_stats(self, suite_name: str, stats: dict, duration: float):
        """Вывод статистики для набора тестов"""
        print(f"\n{Colors.BOLD}📊 Статистика {suite_name}:{Colors.ENDC}")
        print(f"  Всего тестов: {stats['total']}")
        print(f"  ✅ Пройдено: {stats['passed']}")
        print(f"  ❌ Провалено: {stats['failed']}")
        print(f"  ⏭️  Пропущено: {stats['skipped']}")
        print(f"  💥 Ошибок: {stats['errors']}")
        print(f"  ⏱️  Время: {duration:.2f}s")

    def _print_final_report(self, results: dict, total_duration: float):
        """Финальный отчет по всем тестам"""
        self.print_header("Финальный отчет")

        total_tests = sum(r["stats"]["total"] for r in results.values())
        total_passed = sum(r["stats"]["passed"] for r in results.values())
        total_failed = sum(r["stats"]["failed"] for r in results.values())
        total_skipped = sum(r["stats"]["skipped"] for r in results.values())

        print(f"{Colors.BOLD}📈 Общая статистика:{Colors.ENDC}")
        print(f"  Всего наборов: {len(results)}")
        print(f"  Всего тестов: {total_tests}")
        print(f"  ✅ Пройдено: {total_passed}")
        print(f"  ❌ Провалено: {total_failed}")
        print(f"  ⏭️  Пропущено: {total_skipped}")
        print(f"  ⏱️  Общее время: {total_duration:.2f}s")

        print(f"\n{Colors.BOLD}📋 Детали по наборам:{Colors.ENDC}")
        for suite, result in results.items():
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {suite}: {result['duration']:.2f}s")

        # Итоговый вердикт
        all_passed = all(r["success"] for r in results.values())
        if all_passed:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 Все тесты пройдены успешно!{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}{Colors.BOLD}⚠️ Некоторые тесты провалены!{Colors.ENDC}")

    def list_suites(self):
        """Вывод списка доступных наборов тестов"""
        self.print_header("Доступные наборы тестов")

        for name, suite in self.test_suites.items():
            print(f"{Colors.BOLD}{name}:{Colors.ENDC}")
            print(f"  {suite['description']}")
            print(f"  Путь: {suite['path']}")
            print(f"  Таймаут: {suite['timeout']}s\n")

    def list_chains(self):
        """Вывод списка предопределенных цепочек"""
        self.print_header("Предопределенные цепочки тестов")

        for name, chain in self.chains.items():
            print(f"{Colors.BOLD}{name}:{Colors.ENDC} {' → '.join(chain)}")

    def generate_coverage_report(self):
        """Генерация отчета покрытия"""
        print(f"\n{Colors.OKCYAN}📊 Генерация отчета покрытия...{Colors.ENDC}")

        cmd = ["pytest", "--cov=.", "--cov-report=html", "--cov-report=term"]
        subprocess.run(cmd)

        print(f"\n{Colors.OKGREEN}✅ Отчет покрытия создан в htmlcov/index.html{Colors.ENDC}")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="Централизованный запуск тестов BOT_AI_V3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python run_tests.py --suite unit              # Запустить unit тесты
  python run_tests.py --chain quick             # Запустить быструю цепочку
  python run_tests.py --chain unit,ml,database  # Кастомная цепочка
  python run_tests.py --list-suites             # Показать доступные наборы
  python run_tests.py --coverage                # Генерировать отчет покрытия
        """,
    )

    parser.add_argument(
        "--suite",
        "-s",
        choices=["unit", "ml", "database", "integration", "performance", "smoke"],
        help="Запустить конкретный набор тестов",
    )

    parser.add_argument(
        "--chain",
        "-c",
        help="Запустить цепочку тестов (предопределенную или через запятую)",
    )

    parser.add_argument(
        "--list-suites",
        "-ls",
        action="store_true",
        help="Показать доступные наборы тестов",
    )

    parser.add_argument(
        "--list-chains",
        "-lc",
        action="store_true",
        help="Показать предопределенные цепочки",
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Генерировать отчет покрытия после тестов",
    )

    parser.add_argument(
        "--no-stop", action="store_true", help="Не останавливать цепочку при ошибке"
    )

    parser.add_argument("--quiet", "-q", action="store_true", help="Минимальный вывод")

    args = parser.parse_args()

    # Создаем runner
    runner = TestRunner(verbose=not args.quiet)

    # Обработка команд
    if args.list_suites:
        runner.list_suites()
        return

    if args.list_chains:
        runner.list_chains()
        return

    # Запуск тестов
    if args.suite:
        # Запуск одного набора
        success, duration, stats = runner.run_suite(args.suite)
        runner._print_suite_stats(args.suite, stats, duration)

    elif args.chain:
        # Запуск цепочки
        if args.chain in runner.chains:
            # Предопределенная цепочка
            chain = runner.chains[args.chain]
        else:
            # Кастомная цепочка
            chain = [s.strip() for s in args.chain.split(",")]

        runner.run_chain(chain, stop_on_failure=not args.no_stop)

    else:
        # По умолчанию запускаем стандартную цепочку
        runner.run_chain(runner.chains["standard"], stop_on_failure=not args.no_stop)

    # Генерация отчета покрытия
    if args.coverage:
        runner.generate_coverage_report()


if __name__ == "__main__":
    main()
