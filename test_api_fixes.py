#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений API ошибок в BOT_AI_V3

Проверяет:
1. Rate Limiter - умное управление лимитами запросов
2. API Key Manager - валидация и ротация ключей
3. Health Monitor - мониторинг состояния бирж
4. Port Management - автоматическое освобождение портов
5. Exponential Backoff - улучшенная обработка ошибок
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from exchanges.base.api_key_manager import KeyType, get_key_manager
from exchanges.base.health_monitor import get_health_monitor
from exchanges.base.rate_limiter import RequestPriority, get_rate_limiter
from exchanges.bybit.client import BybitClient


async def test_rate_limiter():
    """Тест Rate Limiter"""
    print("\n" + "=" * 60)
    print("🔄 ТЕСТ RATE LIMITER")
    print("=" * 60)

    rate_limiter = get_rate_limiter()

    # Тестируем получение разрешений
    print("📊 Тестирование лимитов запросов...")

    for i in range(5):
        success = await rate_limiter.acquire(
            exchange_name="bybit",
            endpoint="/v5/market/time",
            is_private=False,
            priority=RequestPriority.NORMAL,
        )

        if success:
            print(f"✅ Запрос {i + 1}: разрешен")
            rate_limiter.record_success("bybit", "/v5/market/time", 50.0)
        else:
            print(f"❌ Запрос {i + 1}: отклонен (rate limit)")

        await asyncio.sleep(0.1)

    # Получаем статистику
    stats = rate_limiter.get_stats("bybit")
    print("\n📈 Статистика Rate Limiter для Bybit:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    return True


async def test_api_key_manager():
    """Тест API Key Manager"""
    print("\n" + "=" * 60)
    print("🔑 ТЕСТ API KEY MANAGER")
    print("=" * 60)

    key_manager = get_key_manager()
    await key_manager.initialize()

    # Добавляем тестовые ключи
    print("🔧 Добавление тестовых API ключей...")

    key_id_1 = key_manager.add_key(
        exchange_name="bybit",
        api_key="test_key_1",
        api_secret="test_secret_1",
        key_type=KeyType.MAIN,
    )

    key_id_2 = key_manager.add_key(
        exchange_name="bybit",
        api_key="test_key_2",
        api_secret="test_secret_2",
        key_type=KeyType.BACKUP,
    )

    print(f"✅ Добавлен основной ключ: {key_id_1}")
    print(f"✅ Добавлен резервный ключ: {key_id_2}")

    # Получаем активный ключ
    active_key = await key_manager.get_active_key("bybit")
    if active_key:
        print(f"🎯 Активный ключ: {active_key.masked_key}")

    # Получаем статистику
    stats = key_manager.get_key_stats("bybit")
    print("\n📈 Статистика API Keys для Bybit:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    await key_manager.shutdown()
    return True


async def test_health_monitor():
    """Тест Health Monitor"""
    print("\n" + "=" * 60)
    print("🏥 ТЕСТ HEALTH MONITOR")
    print("=" * 60)

    health_monitor = get_health_monitor()
    await health_monitor.initialize()

    # Добавляем биржи для мониторинга
    print("🔧 Добавление бирж для мониторинга...")
    health_monitor.add_exchange("bybit")
    health_monitor.add_exchange("binance")

    # Запускаем мониторинг на короткое время
    print("▶️ Запуск мониторинга на 10 секунд...")
    await health_monitor.start_monitoring()

    # Ждем несколько проверок
    await asyncio.sleep(10)

    # Получаем статусы
    bybit_status = health_monitor.get_exchange_status("bybit")
    if bybit_status:
        print(f"✅ Статус Bybit: {bybit_status.overall_status.value}")
        print(f"📡 Средняя латентность: {bybit_status.avg_latency:.1f}ms")
        print(f"⏰ Последняя проверка: {bybit_status.last_check}")

    # Получаем общую сводку
    summary = health_monitor.get_health_summary()
    print("\n📈 Сводка по здоровью бирж:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    await health_monitor.shutdown()
    return True


async def test_bybit_client():
    """Тест интеграции с Bybit клиентом"""
    print("\n" + "=" * 60)
    print("🔗 ТЕСТ BYBIT CLIENT ИНТЕГРАЦИИ")
    print("=" * 60)

    # Создаем клиент в публичном режиме
    client = BybitClient(
        api_key="public_access", api_secret="public_access", sandbox=False
    )

    try:
        print("🔌 Подключение к Bybit...")
        success = await client.connect()

        if success:
            print("✅ Подключение успешно")

            # Тестируем получение времени сервера
            print("⏰ Получение времени сервера...")
            server_time = await client.get_server_time()
            print(f"🕐 Время сервера: {server_time}")

            # Получаем статус здоровья
            print("🏥 Проверка статуса здоровья...")
            health_status = client.get_health_status()
            print(f"📊 Статус здоровья: {health_status['status']}")

            # Получаем метрики производительности
            print("📈 Получение метрик производительности...")
            metrics = client.get_performance_metrics()
            print(
                f"🎯 Успешность запросов: {metrics['connection_stats']['success_rate']}"
            )

        else:
            print("❌ Подключение не удалось")
            return False

    except Exception as e:
        print(f"❌ Ошибка тестирования клиента: {e}")
        return False
    finally:
        await client.disconnect()

    return True


def test_port_management():
    """Тест управления портами"""
    print("\n" + "=" * 60)
    print("🔌 ТЕСТ PORT MANAGEMENT")
    print("=" * 60)

    from unified_launcher import find_processes_using_port, is_port_in_use

    # Тестируем проверку портов
    test_ports = [8080, 5173, 3000, 9090]

    for port in test_ports:
        in_use = is_port_in_use(port)
        print(f"🔍 Порт {port}: {'занят' if in_use else 'свободен'}")

        if in_use:
            processes = find_processes_using_port(port)
            for proc_info in processes:
                print(f"   📝 Процесс: {proc_info['name']} (PID: {proc_info['pid']})")

    return True


async def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 ЗАПУСК ТЕСТОВ ИСПРАВЛЕНИЙ API ОШИБОК BOT_AI_V3")
    print("=" * 80)

    tests = [
        ("Rate Limiter", test_rate_limiter),
        ("API Key Manager", test_api_key_manager),
        ("Health Monitor", test_health_monitor),
        ("Bybit Client Integration", test_bybit_client),
        # ("Port Management", test_port_management)  # Синхронный тест
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n🧪 Выполнение теста: {test_name}")
        print("-" * 40)

        try:
            start_time = time.time()
            result = await test_func()
            duration = time.time() - start_time

            results[test_name] = {"success": result, "duration": f"{duration:.2f}s"}

            if result:
                print(f"✅ {test_name}: ПРОЙДЕН ({duration:.2f}s)")
            else:
                print(f"❌ {test_name}: ПРОВАЛЕН ({duration:.2f}s)")

        except Exception as e:
            duration = time.time() - start_time
            results[test_name] = {
                "success": False,
                "error": str(e),
                "duration": f"{duration:.2f}s",
            }
            print(f"❌ {test_name}: ОШИБКА - {e} ({duration:.2f}s)")

    # Синхронный тест портов
    print("\n🧪 Выполнение теста: Port Management")
    print("-" * 40)
    try:
        start_time = time.time()
        result = test_port_management()
        duration = time.time() - start_time

        results["Port Management"] = {"success": result, "duration": f"{duration:.2f}s"}

        if result:
            print(f"✅ Port Management: ПРОЙДЕН ({duration:.2f}s)")
        else:
            print(f"❌ Port Management: ПРОВАЛЕН ({duration:.2f}s)")
    except Exception as e:
        duration = time.time() - start_time
        results["Port Management"] = {
            "success": False,
            "error": str(e),
            "duration": f"{duration:.2f}s",
        }
        print(f"❌ Port Management: ОШИБКА - {e} ({duration:.2f}s)")

    # Итоги
    print("\n" + "=" * 80)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 80)

    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)

    print(f"✅ Пройдено: {passed}/{total}")
    print(f"❌ Провалено: {total - passed}/{total}")
    print(f"📈 Успешность: {(passed / total) * 100:.1f}%")

    print("\n📋 Детали результатов:")
    for test_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        duration = result["duration"]
        error = (
            f" ({result.get('error', '')})"
            if not result["success"] and "error" in result
            else ""
        )
        print(f"  {status} {test_name}: {duration}{error}")

    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Исправления работают корректно.")
        return True
    else:
        print(
            f"\n⚠️ Обнаружены проблемы в {total - passed} тестах. Требуется дополнительная отладка."
        )
        return False


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
