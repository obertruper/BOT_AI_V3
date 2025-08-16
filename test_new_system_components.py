#!/usr/bin/env python3
"""
Тестирование новых системных компонентов BOT_AI_V3
"""

import asyncio
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_worker_coordinator():
    """Тестирование координатора воркеров"""
    logger.info("🧪 Тестирование WorkerCoordinator...")

    try:
        from core.system.worker_coordinator import worker_coordinator

        # Запуск координатора
        await worker_coordinator.start()

        # Регистрация тестового воркера
        worker_id = await worker_coordinator.register_worker(
            worker_type="test_worker", metadata={"test": True, "version": "1.0"}
        )

        if worker_id:
            logger.info(f"✅ Воркер зарегистрирован: {worker_id}")

            # Отправка heartbeat
            success = await worker_coordinator.heartbeat(worker_id, status="running")
            logger.info(f"✅ Heartbeat отправлен: {success}")

            # Получение статистики
            stats = worker_coordinator.get_worker_stats()
            logger.info(f"✅ Статистика воркеров: {len(stats.get('workers', []))}")

            # Снятие с регистрации
            await worker_coordinator.unregister_worker(worker_id)
            logger.info("✅ Воркер снят с регистрации")

        await worker_coordinator.stop()
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования WorkerCoordinator: {e}")
        return False


async def test_signal_deduplicator():
    """Тестирование дедупликатора сигналов"""
    logger.info("🧪 Тестирование SignalDeduplicator...")

    try:
        from core.system.signal_deduplicator import signal_deduplicator

        # Тестовый сигнал
        signal_data = {
            "symbol": "BTCUSDT",
            "direction": "BUY",
            "strategy": "test_strategy",
            "timestamp": datetime.now(),
            "signal_strength": 0.8,
            "price_level": 50000.0,
        }

        # Первая проверка - должна быть уникальной
        is_unique1 = await signal_deduplicator.check_and_register_signal(signal_data)
        logger.info(f"✅ Первый сигнал уникален: {is_unique1}")

        # Вторая проверка того же сигнала - должна быть дубликатом
        is_unique2 = await signal_deduplicator.check_and_register_signal(signal_data)
        logger.info(f"✅ Второй сигнал дубликат: {not is_unique2}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования SignalDeduplicator: {e}")
        return False


async def main():
    """Главная функция"""
    logger.info("🚀 Начало тестирования новых системных компонентов")

    tests = [
        ("WorkerCoordinator", test_worker_coordinator),
        ("SignalDeduplicator", test_signal_deduplicator),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'=' * 30}")
            logger.info(f"Запуск теста: {test_name}")
            logger.info(f"{'=' * 30}")

            result = await test_func()
            results[test_name] = result

            status = "✅ УСПЕХ" if result else "❌ ОШИБКА"
            logger.info(f"{status}: {test_name}")

        except Exception as e:
            logger.error(f"❌ Критическая ошибка в тесте {test_name}: {e}")
            results[test_name] = False

    # Итоговый отчет
    logger.info(f"\n{'=' * 30}")
    logger.info("ИТОГОВЫЙ ОТЧЕТ")
    logger.info(f"{'=' * 30}")

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        logger.info(f"{test_name}: {status}")

    logger.info(f"\nРезультат: {passed}/{total} тестов пройдено")

    if passed == total:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        logger.warning(f"⚠️  {total - passed} тестов провалено")
        return False


if __name__ == "__main__":
    asyncio.run(main())
