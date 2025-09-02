#!/usr/bin/env python3
"""
🎯 ГЛАВНАЯ ТОЧКА ВХОДА В ТЕСТОВУЮ СИСТЕМУ BOT_AI_V3

Единая точка запуска всех тестовых компонентов:
- Unit тесты
- Integration тесты
- Performance тесты
- E2E тесты
- Dynamic SL/TP тесты
- Code Quality проверки

Использование:
    python3 orchestrator_main.py                    # Интерактивный режим
    python3 orchestrator_main.py --mode quick       # Быстрые тесты
    python3 orchestrator_main.py --mode full        # Полное тестирование
    python3 orchestrator_main.py --mode dynamic-sltp # Dynamic SL/TP тесты
    python3 orchestrator_main.py --help             # Справка
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Импортируем оркестратор
try:
    from scripts.unified_test_orchestrator import UnifiedTestOrchestrator
except ImportError as e:
    print(f"❌ Error importing UnifiedTestOrchestrator: {e}")
    print("💡 Make sure you're running from the project root directory")
    sys.exit(1)

# Импортируем run_tests для CLI режима
try:
    from run_tests import TestRunner
except ImportError:
    TestRunner = None

# Импортируем Position Tracker тесты
try:
    from tests.position_tracker_test_suite import PositionTrackerTestSuite
except ImportError:
    PositionTrackerTestSuite = None


class Colors:
    """ANSI цвета для терминала"""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_welcome():
    """Приветственное сообщение"""
    print(f"\n{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}🎯 BOT_AI_V3 UNIFIED TEST ORCHESTRATOR 🎯{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.CYAN}🚀 Единая точка входа для всего тестирования системы{Colors.ENDC}")
    print(f"{Colors.BLUE}📊 Включает Dynamic SL/TP тесты и полную интеграцию{Colors.ENDC}")
    print(f"{Colors.GREEN}✨ Интерактивный режим с визуальными отчетами{Colors.ENDC}")
    print(f"{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")


async def run_position_tracker_tests(args):
    """Запуск Position Tracker тестов"""
    if PositionTrackerTestSuite is None:
        print(f"{Colors.FAIL}❌ Position Tracker Test Suite недоступен{Colors.ENDC}")
        return

    print(f"{Colors.BLUE}🎯 Запуск Position Tracker Test Suite...{Colors.ENDC}\n")

    suite = PositionTrackerTestSuite()

    try:
        # Запускаем все тесты Position Tracker
        await suite.run_all_tests(verbose=args.verbose)

        # Выводим отчет
        suite.print_summary()

        # Генерируем HTML отчет если запрошено
        if args.generate_report:
            await suite.generate_html_report()
            print(
                f"{Colors.GREEN}📄 HTML отчет сохранен в test_results/position_tracker_report.html{Colors.ENDC}"
            )

    except Exception as e:
        print(f"{Colors.FAIL}❌ Ошибка выполнения Position Tracker тестов: {e}{Colors.ENDC}")
        if args.verbose:
            import traceback

            traceback.print_exc()


def print_help():
    """Справочная информация"""
    help_text = f"""
{Colors.BOLD}🎯 РЕЖИМЫ РАБОТЫ:{Colors.ENDC}

{Colors.CYAN}Интерактивный режим:{Colors.ENDC}
  python3 orchestrator_main.py

  Полнофункциональное меню с возможностью:
  - Выбора конкретных компонентов
  - Запуска Dynamic SL/TP suite
  - Генерации HTML отчетов
  - Визуального мониторинга

{Colors.CYAN}CLI режимы:{Colors.ENDC}
  --mode quick          Быстрые smoke и unit тесты
  --mode standard       Unit + ML + Database тесты
  --mode full           Полное тестирование всех компонентов
  --mode dynamic-sltp   Только Dynamic SL/TP тесты
  --mode position-tracker Только Position Tracker тесты
  --mode performance    Только performance тесты
  --mode integration    Только integration тесты
  --mode ci             CI/CD оптимизированные тесты

{Colors.CYAN}Специальные режимы:{Colors.ENDC}
  --mode visual         Генерация визуальных отчетов
  --mode analysis       Code analysis и качество кода
  --mode coverage       Coverage анализ с детальными отчетами

{Colors.CYAN}Параметры:{Colors.ENDC}
  --verbose, -v         Подробный вывод
  --quiet, -q           Минимальный вывод
  --timeout SECONDS     Таймаут для тестов (по умолчанию 1800)
  --parallel            Параллельное выполнение тестов
  --generate-report     Генерировать HTML отчет после завершения
  --output-dir DIR      Директория для отчетов

{Colors.BOLD}🔧 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:{Colors.ENDC}

# Интерактивный режим (рекомендуется)
python3 orchestrator_main.py

# Быстрая проверка перед коммитом
python3 orchestrator_main.py --mode quick --generate-report

# Полное тестирование с параллелизмом
python3 orchestrator_main.py --mode full --parallel --verbose

# Только Dynamic SL/TP тесты
python3 orchestrator_main.py --mode dynamic-sltp --verbose

# Только Position Tracker тесты
python3 orchestrator_main.py --mode position-tracker --verbose

# CI/CD режим
python3 orchestrator_main.py --mode ci --quiet --timeout 600

{Colors.BOLD}📊 DYNAMIC SL/TP ТЕСТЫ:{Colors.ENDC}

Специализированный набор тестов для динамических Stop Loss/Take Profit:
- Unit тесты калькулятора
- Integration тесты с ML сигналами
- Performance тесты скорости расчета
- E2E тесты полного пайплайна
- Stress тесты различных рыночных условий

{Colors.BOLD}📍 POSITION TRACKER ТЕСТЫ:{Colors.ENDC}

Комплексное тестирование Enhanced Position Tracker:
- Unit тесты основной функциональности
- Integration тесты с БД и биржами
- Performance тесты производительности
- API Integration тесты
- Error handling и stress тесты

{Colors.BOLD}📁 СТРУКТУРА ОТЧЕТОВ:{Colors.ENDC}

test_results/
├── dashboard.html          # Главный дашборд
├── detailed_report.json    # Детализированные результаты
├── coverage/              # Coverage отчеты
├── performance/           # Performance метрики
└── dynamic_sltp/         # Специальные отчеты для SL/TP

{Colors.GREEN}💡 Совет: Начните с интерактивного режима для знакомства с системой{Colors.ENDC}
"""
    print(help_text)


async def run_cli_mode(mode: str, args):
    """Запуск в CLI режиме"""
    print(f"{Colors.BLUE}🚀 Запуск в режиме: {mode}{Colors.ENDC}\n")

    orchestrator = UnifiedTestOrchestrator()

    if mode == "interactive":
        await orchestrator.run_interactive()

    elif mode == "quick":
        # Быстрые тесты
        for key in orchestrator.components:
            orchestrator.components[key]["enabled"] = key in ["unit_tests", "smoke"]
        await orchestrator.run_cli("quick")

    elif mode == "standard":
        # Стандартные тесты
        for key in orchestrator.components:
            orchestrator.components[key]["enabled"] = key in [
                "unit_tests",
                "ml_tests",
                "database_tests",
            ]
        await orchestrator.run_cli("standard")

    elif mode == "full":
        # Полное тестирование
        await orchestrator.run_cli("full")

    elif mode == "dynamic-sltp":
        # Только Dynamic SL/TP тесты
        await orchestrator.run_dynamic_sltp_suite()

    elif mode == "position-tracker":
        # Только Position Tracker тесты
        await run_position_tracker_tests(args)

    elif mode == "performance":
        # Performance тесты
        for key in orchestrator.components:
            orchestrator.components[key]["enabled"] = key in [
                "performance_tests",
                "dynamic_sltp_performance_tests",
            ]
        await orchestrator.run_all_enabled()

    elif mode == "integration":
        # Integration тесты
        for key in orchestrator.components:
            orchestrator.components[key]["enabled"] = key in [
                "integration_tests",
                "dynamic_sltp_integration_tests",
                "dynamic_sltp_e2e_tests",
            ]
        await orchestrator.run_all_enabled()

    elif mode == "ci":
        # CI оптимизированные тесты
        for key in orchestrator.components:
            orchestrator.components[key]["enabled"] = key in [
                "unit_tests",
                "ml_tests",
                "code_quality",
                "security_check",
            ]
        await orchestrator.run_all_enabled()

    elif mode == "visual":
        # Генерация отчетов
        orchestrator.generate_html_dashboard()
        print(f"{Colors.GREEN}✅ Visual dashboard generated{Colors.ENDC}")
        return

    elif mode == "analysis":
        # Code analysis
        for key in orchestrator.components:
            orchestrator.components[key]["enabled"] = key in [
                "code_quality",
                "type_check",
                "security_check",
                "code_usage_analyzer_tests",
                "code_analyzer_validation_tests",
            ]
        await orchestrator.run_all_enabled()

    elif mode == "coverage":
        # Coverage анализ
        for key in orchestrator.components:
            orchestrator.components[key]["enabled"] = key in [
                "coverage_report",
                "unit_tests",
                "integration_tests",
            ]
        await orchestrator.run_all_enabled()

    else:
        print(f"{Colors.FAIL}❌ Неизвестный режим: {mode}{Colors.ENDC}")
        print(f"{Colors.CYAN}💡 Используйте --help для просмотра доступных режимов{Colors.ENDC}")
        return

    # Генерация отчета если запрошено
    if args.generate_report:
        print(f"\n{Colors.GREEN}📊 Генерация HTML отчета...{Colors.ENDC}")
        orchestrator.generate_html_dashboard()

    print(f"\n{Colors.GREEN}✅ Тестирование завершено!{Colors.ENDC}")
    print(f"{Colors.BLUE}📁 Результаты сохранены в: test_results/{Colors.ENDC}")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="🎯 BOT_AI_V3 Unified Test Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Используйте интерактивный режим для полного контроля над тестированием",
    )

    parser.add_argument(
        "--mode",
        choices=[
            "interactive",
            "quick",
            "standard",
            "full",
            "dynamic-sltp",
            "position-tracker",
            "performance",
            "integration",
            "ci",
            "visual",
            "analysis",
            "coverage",
        ],
        default="interactive",
        help="Режим работы оркестратора",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")

    parser.add_argument("--quiet", "-q", action="store_true", help="Минимальный вывод")

    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Таймаут для тестов в секундах (по умолчанию 1800)",
    )

    parser.add_argument("--parallel", action="store_true", help="Параллельное выполнение тестов")

    parser.add_argument(
        "--generate-report", action="store_true", help="Генерировать HTML отчет после завершения"
    )

    parser.add_argument(
        "--output-dir", default="test_results", help="Директория для сохранения отчетов"
    )

    parser.add_argument("--help-detailed", action="store_true", help="Показать детальную справку")

    args = parser.parse_args()

    # Детальная справка
    if args.help_detailed:
        print_help()
        return

    # Проверяем конфликты параметров
    if args.verbose and args.quiet:
        print(
            f"{Colors.WARNING}⚠️  Нельзя использовать --verbose и --quiet одновременно{Colors.ENDC}"
        )
        return

    # Приветствие (если не quiet режим)
    if not args.quiet:
        print_welcome()

    try:
        # Запуск в соответствующем режиме
        asyncio.run(run_cli_mode(args.mode, args))

    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}🛑 Прервано пользователем{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}❌ Ошибка: {e}{Colors.ENDC}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
