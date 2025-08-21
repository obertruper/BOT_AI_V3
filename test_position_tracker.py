#!/usr/bin/env python3
"""
🎯 Быстрый запуск тестов Enhanced Position Tracker

Этот скрипт предоставляет удобный интерфейс для тестирования
Position Tracker без необходимости использования orchestrator_main.py

Использование:
    python3 test_position_tracker.py                # Все тесты
    python3 test_position_tracker.py --unit         # Только unit тесты
    python3 test_position_tracker.py --integration  # Только integration тесты
    python3 test_position_tracker.py --performance  # Только performance тесты
    python3 test_position_tracker.py --quick        # Быстрые тесты (unit только)
    python3 test_position_tracker.py --html         # С HTML отчетом
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.position_tracker_test_suite import PositionTrackerTestSuite


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


def print_banner():
    """Выводит заголовок"""
    print(f"\n{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}🎯 ENHANCED POSITION TRACKER TEST RUNNER{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*70}{Colors.ENDC}")
    print(f"{Colors.CYAN}🚀 Комплексное тестирование системы отслеживания позиций{Colors.ENDC}")
    print(f"{Colors.BLUE}📊 Unit • Integration • Performance тесты{Colors.ENDC}\n")


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="Enhanced Position Tracker Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  python3 test_position_tracker.py                # Все тесты
  python3 test_position_tracker.py --unit         # Только unit тесты
  python3 test_position_tracker.py --integration  # Только integration тесты
  python3 test_position_tracker.py --performance  # Только performance тесты
  python3 test_position_tracker.py --quick        # Быстрые тесты
  python3 test_position_tracker.py --html -v      # С HTML отчетом и подробным выводом
        """
    )
    
    # Группа для выбора типа тестов
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--unit", action="store_true", help="Запустить только unit тесты")
    test_group.add_argument("--integration", action="store_true", help="Запустить только integration тесты")
    test_group.add_argument("--performance", action="store_true", help="Запустить только performance тесты")
    test_group.add_argument("--quick", action="store_true", help="Быстрые тесты (только unit)")
    
    # Опции
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")
    parser.add_argument("--html", action="store_true", help="Генерировать HTML отчет")
    parser.add_argument("--quiet", "-q", action="store_true", help="Минимальный вывод")
    
    args = parser.parse_args()
    
    # Проверяем конфликты
    if args.verbose and args.quiet:
        print(f"{Colors.WARNING}⚠️ Нельзя использовать --verbose и --quiet одновременно{Colors.ENDC}")
        return 1
    
    # Выводим баннер если не quiet режим
    if not args.quiet:
        print_banner()
    
    # Создаем тестовый набор
    suite = PositionTrackerTestSuite()
    
    try:
        # Определяем какие тесты запускать
        if args.unit or args.quick:
            print(f"{Colors.BLUE}🔧 Запуск Unit тестов Position Tracker{Colors.ENDC}")
            result = await suite.run_unit_tests(verbose=args.verbose)
            suite.test_results = {"unit": result}
            
        elif args.integration:
            print(f"{Colors.BLUE}🔗 Запуск Integration тестов Position Tracker{Colors.ENDC}")
            result = await suite.run_integration_tests(verbose=args.verbose)
            suite.test_results = {"integration": result}
            
        elif args.performance:
            print(f"{Colors.BLUE}⚡ Запуск Performance тестов Position Tracker{Colors.ENDC}")
            result = await suite.run_performance_tests(verbose=args.verbose)
            suite.test_results = {"performance": result}
            
        else:
            # Все тесты по умолчанию
            print(f"{Colors.BLUE}🎯 Запуск всех тестов Position Tracker{Colors.ENDC}")
            await suite.run_all_tests(verbose=args.verbose)
        
        # Выводим отчет
        if not args.quiet:
            suite.print_summary()
        
        # Генерируем HTML отчет если запрошено
        if args.html:
            await suite.generate_html_report()
            print(f"{Colors.GREEN}📄 HTML отчет сохранен: test_results/position_tracker_report.html{Colors.ENDC}")
        
        # Определяем успешность выполнения
        summary = suite.test_results.get("summary")
        if summary:
            overall_success = summary.get("overall_success", False)
        else:
            # Если запускался только один тип тестов
            overall_success = any(
                result.get("success", False) 
                for result in suite.test_results.values()
            )
        
        if not args.quiet:
            if overall_success:
                print(f"\n{Colors.GREEN}🎉 Все тесты Position Tracker завершились успешно!{Colors.ENDC}")
            else:
                print(f"\n{Colors.FAIL}❌ Некоторые тесты завершились с ошибками{Colors.ENDC}")
        
        return 0 if overall_success else 1
        
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}🛑 Тестирование прервано пользователем{Colors.ENDC}")
        return 130
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Критическая ошибка: {e}{Colors.ENDC}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)