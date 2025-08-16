#!/usr/bin/env python3
"""
Тестирование системных компонентов v2
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_components():
    """Тест компонентов по отдельности"""

    results = {}

    # 1. Тест WorkerCoordinator
    try:
        logger.info("\n=== Тест WorkerCoordinator ===")
        from core.system.worker_coordinator import worker_coordinator

        await worker_coordinator.start()
        worker_id = await worker_coordinator.register_worker(
            worker_type="test_worker", metadata={"test": True}
        )

        if worker_id:
            await worker_coordinator.heartbeat(worker_id, status="running", active_tasks=1)
            await worker_coordinator.unregister_worker(worker_id)
            logger.info("✅ WorkerCoordinator работает")
            results["WorkerCoordinator"] = "OK"
        else:
            logger.warning("⚠️ WorkerCoordinator - дубликат")
            results["WorkerCoordinator"] = "DUPLICATE"

        await worker_coordinator.stop()

    except Exception as e:
        logger.error(f"❌ WorkerCoordinator: {e}")
        results["WorkerCoordinator"] = f"ERROR: {e}"

    # 2. Тест SignalDeduplicator
    try:
        logger.info("\n=== Тест SignalDeduplicator ===")
        from core.system.signal_deduplicator import signal_deduplicator

        signal = {
            "symbol": "BTCUSDT",
            "direction": "BUY",
            "strategy": "test",
            "timestamp": datetime.now(),
            "signal_strength": 0.8,
            "price_level": 50000,
        }

        is_unique = await signal_deduplicator.check_and_register_signal(signal)
        is_duplicate = await signal_deduplicator.check_and_register_signal(signal)

        if is_unique and not is_duplicate:
            logger.info("✅ SignalDeduplicator работает")
            results["SignalDeduplicator"] = "OK"
        else:
            logger.error("❌ SignalDeduplicator не работает корректно")
            results["SignalDeduplicator"] = "FAILED"

    except Exception as e:
        logger.error(f"❌ SignalDeduplicator: {e}")
        results["SignalDeduplicator"] = f"ERROR: {e}"

    # 3. Тест BalanceManager
    try:
        logger.info("\n=== Тест BalanceManager ===")
        from core.system.balance_manager import balance_manager

        await balance_manager.start()

        # Обновляем тестовый баланс
        success = await balance_manager.update_balance(
            exchange="bybit",
            symbol="USDT",
            total=Decimal("1000"),
            available=Decimal("900"),
            locked=Decimal("100"),
        )

        if success:
            # Проверяем доступность
            available, error = await balance_manager.check_balance_availability(
                exchange="bybit", symbol="USDT", amount=Decimal("100")
            )

            if available:
                logger.info("✅ BalanceManager работает")
                results["BalanceManager"] = "OK"
            else:
                logger.warning(f"⚠️ BalanceManager: {error}")
                results["BalanceManager"] = f"WARNING: {error}"

        await balance_manager.stop()

    except Exception as e:
        logger.error(f"❌ BalanceManager: {e}")
        results["BalanceManager"] = f"ERROR: {e}"

    # 4. Тест RateLimiter
    try:
        logger.info("\n=== Тест RateLimiter ===")
        from core.system.rate_limiter import rate_limiter

        wait_time = await rate_limiter.acquire("bybit", "market_data")

        if wait_time >= 0:
            logger.info(f"✅ RateLimiter работает (wait: {wait_time}s)")
            results["RateLimiter"] = "OK"
        else:
            logger.error("❌ RateLimiter вернул отрицательное время")
            results["RateLimiter"] = "FAILED"

    except Exception as e:
        logger.error(f"❌ RateLimiter: {e}")
        results["RateLimiter"] = f"ERROR: {e}"

    # 5. Тест ProcessMonitor
    try:
        logger.info("\n=== Тест ProcessMonitor ===")
        from core.system.process_monitor import process_monitor

        await process_monitor.start()

        success = await process_monitor.register_component(
            "test_component", metadata={"test": True}
        )

        if success:
            await process_monitor.heartbeat("test_component", status="healthy", active_tasks=1)

            health = process_monitor.get_component_health("test_component")

            if health and health.get("status"):
                logger.info("✅ ProcessMonitor работает")
                results["ProcessMonitor"] = "OK"
            else:
                logger.warning("⚠️ ProcessMonitor - нет данных о здоровье")
                results["ProcessMonitor"] = "WARNING"

        await process_monitor.stop()

    except Exception as e:
        logger.error(f"❌ ProcessMonitor: {e}")
        results["ProcessMonitor"] = f"ERROR: {e}"

    # Итоговый отчет
    logger.info("\n" + "=" * 60)
    logger.info("📊 ИТОГОВЫЙ ОТЧЕТ")
    logger.info("=" * 60)

    ok_count = sum(1 for v in results.values() if v == "OK")
    total = len(results)

    for component, status in results.items():
        if status == "OK":
            logger.info(f"✅ {component}: {status}")
        elif "WARNING" in str(status) or status == "DUPLICATE":
            logger.warning(f"⚠️  {component}: {status}")
        else:
            logger.error(f"❌ {component}: {status}")

    logger.info(f"\n📈 Результат: {ok_count}/{total} компонентов работают")

    if ok_count == total:
        logger.info("🎉 Все компоненты работают корректно!")
    elif ok_count >= total * 0.8:
        logger.info("✅ Система работоспособна с небольшими проблемами")
    elif ok_count >= total * 0.5:
        logger.warning("⚠️  Система частично работоспособна")
    else:
        logger.error("❌ Система не работоспособна")


if __name__ == "__main__":
    asyncio.run(test_components())
