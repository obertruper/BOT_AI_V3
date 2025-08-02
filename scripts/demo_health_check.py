#!/usr/bin/env python3
"""
Демонстрация работы health check функциональности
"""

import asyncio
import json
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.system.health_checker import HealthChecker


async def demo_health_checker():
    """Демонстрация работы HealthChecker"""

    print("=" * 60)
    print("BOT Trading v3 - Health Check Демонстрация")
    print("=" * 60)

    # Инициализируем ConfigManager
    config_manager = ConfigManager()
    await config_manager.initialize()

    # Создаем HealthChecker
    health_checker = HealthChecker(config_manager)

    print("\n1. Проверка всех компонентов системы...")
    print("-" * 40)

    try:
        # Выполняем проверку всех компонентов
        results = await health_checker.check_all_components()

        print("\nРезультаты проверки компонентов:")
        for component, status in results.items():
            icon = "✅" if status == "healthy" else "⚠️" if status == "warning" else "❌"
            print(f"  {icon} {component}: {status}")

        # Получаем детальный отчет
        print("\n2. Получение детального отчета...")
        print("-" * 40)

        detailed_report = await health_checker.get_detailed_report()

        print(f"\nОбщий статус системы: {detailed_report['overall_status']}")
        print(f"Время проверки: {detailed_report['timestamp']}")

        if "details" in detailed_report and "system" in detailed_report["details"]:
            system_info = detailed_report["details"]["system"]

            print("\nСистемные ресурсы:")
            print(
                f"  CPU: {system_info['cpu']['percent']}% ({system_info['cpu']['cores']} ядер)"
            )
            print(
                f"  RAM: {system_info['memory']['percent']}% "
                f"({system_info['memory']['available_gb']:.1f} GB доступно из "
                f"{system_info['memory']['total_gb']:.1f} GB)"
            )
            print(
                f"  Диск: {system_info['disk']['percent']}% "
                f"({system_info['disk']['free_gb']:.1f} GB свободно из "
                f"{system_info['disk']['total_gb']:.1f} GB)"
            )

        # Проверка отдельных компонентов
        print("\n3. Проверка отдельных компонентов...")
        print("-" * 40)

        # Проверка БД
        print("\nПроверка PostgreSQL...")
        db_status = await health_checker.check_database()
        print(f"  Статус БД: {db_status}")

        # Проверка Redis
        print("\nПроверка Redis...")
        redis_status = await health_checker.check_redis()
        print(f"  Статус Redis: {redis_status}")

        # Проверка системных ресурсов
        print("\nПроверка системных ресурсов...")
        resources_status = await health_checker.check_system_resources()
        print(f"  Статус ресурсов: {resources_status}")

        # Сохраняем отчет в файл
        print("\n4. Сохранение отчета...")
        print("-" * 40)

        report_path = Path("data/logs/health_check_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(detailed_report, f, indent=2, ensure_ascii=False)

        print(f"  Отчет сохранен в: {report_path}")

    except Exception as e:
        print(f"\n❌ Ошибка при проверке: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Демонстрация завершена")
    print("=" * 60)


async def demo_api_health_check():
    """Демонстрация работы через API"""

    print("\n\n5. Проверка через API...")
    print("-" * 40)

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/api/health")

            if response.status_code == 200:
                data = response.json()
                print("\nОтвет API:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"  API недоступен (код: {response.status_code})")
    except Exception as e:
        print(f"  Не удалось подключиться к API: {e}")
        print("  Убедитесь, что веб-сервер запущен (python web/launcher.py)")


if __name__ == "__main__":
    print("Запуск демонстрации health check...")

    # Запускаем демонстрацию
    asyncio.run(demo_health_checker())

    # Пробуем API если доступен
    asyncio.run(demo_api_health_check())
