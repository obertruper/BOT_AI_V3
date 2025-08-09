#!/usr/bin/env python3
"""
Скрипт для быстрого тестирования TestingAgent

Использование:
    python test_testing_agent.py --action=ports          # Проверить порты
    python test_testing_agent.py --action=logs           # Анализ логов
    python test_testing_agent.py --action=diagnosis      # Полная диагностика
    python test_testing_agent.py --action=monitor        # Мониторинг системы
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from agents.testing_agent import TestingAgent


async def test_ports_fix(agent: TestingAgent):
    """Тестирование исправления конфликтов портов"""
    print("🔍 Тестирование исправления конфликтов портов...")
    await agent.fix_port_conflicts()
    print("✅ Тестирование портов завершено")


async def test_logs_analysis(agent: TestingAgent):
    """Тестирование анализа логов"""
    print("🔍 Тестирование анализа логов...")

    # Пример тестовых логов с ошибками
    test_logs = """
2025-08-04 12:00:00 INFO - Starting system...
2025-08-04 12:00:01 ERROR - ModuleNotFoundError: No module named 'passlib'
2025-08-04 12:00:02 INFO - Retrying connection...
2025-08-04 12:00:03 ERROR - Address already in use on port 8080
2025-08-04 12:00:04 CRITICAL - Database connection failed
2025-08-04 12:00:05 WARNING - ML model not found
"""

    errors = await agent.analyze_errors(test_logs)

    if errors:
        print(f"✅ Обнаружено {len(errors)} ошибок:")
        for error in errors:
            print(f"   - {error['type']}: {error['line']}")
    else:
        print("ℹ️ Ошибок не найдено")


async def test_full_diagnosis(agent: TestingAgent):
    """Полная диагностика системы"""
    print("🔍 Запуск полной диагностики системы...")

    # Проверка портов
    await test_ports_fix(agent)

    # Анализ логов (если есть)
    log_files = [
        agent.logs_dir / "system.log",
        agent.logs_dir / "core.log",
        agent.logs_dir / "api.log",
        agent.logs_dir / "errors.log",
    ]

    found_errors = False
    for log_file in log_files:
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content:
                        errors = await agent.analyze_errors(content)
                        if errors:
                            print(f"❌ В {log_file.name} найдено ошибок: {len(errors)}")
                            for error in errors[-3:]:  # Показываем последние 3
                                print(f"   - {error['type']}: {error['line'][:80]}...")
                            found_errors = True
            except Exception as e:
                print(f"⚠️ Ошибка при чтении {log_file}: {e}")

    if not found_errors:
        print("✅ В логах критических ошибок не найдено")

    # Отчет
    report = agent.get_error_report()
    print("\n📊 Итоговый отчет:")
    print(f"   Всего ошибок обработано: {report['total_errors']}")
    print(f"   Типы ошибок: {report['error_types']}")


async def test_system_monitoring(agent: TestingAgent):
    """Тестирование мониторинга системы"""
    print("🔍 Тестирование мониторинга системы (10 секунд)...")

    # Запускаем краткий мониторинг
    try:
        await asyncio.wait_for(agent.start_system_monitoring("core"), timeout=10.0)
    except asyncio.TimeoutError:
        print("⏰ Тайм-аут мониторинга (это нормально для теста)")
        await agent.stop_monitoring()
    except Exception as e:
        print(f"⚠️ Ошибка при мониторинге: {e}")


async def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description="Тестирование TestingAgent")
    parser.add_argument(
        "--action",
        choices=["ports", "logs", "diagnosis", "monitor"],
        default="diagnosis",
        help="Действие для выполнения",
    )

    args = parser.parse_args()

    # Создаем агент
    agent = TestingAgent()

    # Выполняем действие
    try:
        if args.action == "ports":
            await test_ports_fix(agent)
        elif args.action == "logs":
            await test_logs_analysis(agent)
        elif args.action == "diagnosis":
            await test_full_diagnosis(agent)
        elif args.action == "monitor":
            await test_system_monitoring(agent)

        print("\n🎉 Все тесты TestingAgent завершены успешно!")

    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
    finally:
        await agent.stop_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
