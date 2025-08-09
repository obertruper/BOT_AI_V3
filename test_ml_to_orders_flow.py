#!/usr/bin/env python3
"""
Тест полного потока ML -> Orders
Проверяет всю цепочку от генерации ML сигнала до создания ордеров
"""

import asyncio
import logging
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Добавляем путь к проекту
sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from core.config.config_manager import ConfigManager
from core.system.orchestrator import SystemOrchestrator


async def test_ml_to_orders_flow():
    """Тестирование полного потока ML -> Orders"""

    config_manager = None
    orchestrator = None

    try:
        logger.info("=" * 80)
        logger.info("🚀 Запуск теста полного потока ML -> Orders")
        logger.info("=" * 80)

        # 1. Инициализация конфигурации
        logger.info("\n📋 Шаг 1: Инициализация конфигурации...")
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Проверяем конфигурацию ML
        ml_config = config.get("ml", {})
        if not ml_config.get("enabled", True):
            logger.warning("ML отключен в конфигурации!")
            return

        logger.info("✅ Конфигурация загружена, ML включен")
        logger.info(f"   Символы: {ml_config.get('symbols', [])}")
        logger.info(f"   Интервал: {ml_config.get('signal_interval_seconds', 60)}с")

        # 2. Создание и инициализация оркестратора
        logger.info("\n📋 Шаг 2: Создание системного оркестратора...")
        orchestrator = SystemOrchestrator(config_manager)

        # 3. Инициализация системы
        logger.info("\n📋 Шаг 3: Инициализация всех компонентов...")
        await orchestrator.initialize()

        # Проверяем что все компоненты инициализированы
        if not orchestrator.trading_engine:
            logger.error("Trading Engine не инициализирован!")
            return

        if not orchestrator.signal_scheduler:
            logger.error("Signal Scheduler не инициализирован!")
            return

        logger.info("✅ Все компоненты инициализированы")

        # 4. Запуск системы
        logger.info("\n📋 Шаг 4: Запуск системы...")
        await orchestrator.start()

        # 5. Проверяем статус
        status = await orchestrator.get_status()
        logger.info("\n📊 Статус системы:")
        logger.info(f"   Компоненты: {status['components']}")
        logger.info(
            f"   Trading Engine: {orchestrator.trading_engine.get_status()['state']}"
        )

        # 6. Ждем генерации сигналов
        logger.info("\n📋 Шаг 5: Ожидание генерации ML сигналов...")
        logger.info("⏳ Ждем 2 минуты для генерации первых сигналов...")

        # Мониторим метрики Trading Engine
        for i in range(12):  # 12 * 10 сек = 2 минуты
            await asyncio.sleep(10)

            # Получаем метрики
            engine_status = orchestrator.trading_engine.get_status()
            metrics = engine_status["metrics"]
            queues = engine_status["queue_sizes"]

            logger.info(f"\n⏱️ [{i + 1}/12] Метрики Trading Engine:")
            logger.info(f"   Обработано сигналов: {metrics['signals_processed']}")
            logger.info(f"   Выполнено ордеров: {metrics['orders_executed']}")
            logger.info(f"   Активных позиций: {metrics['active_positions']}")
            logger.info(f"   Очередь сигналов: {queues['signals']}")
            logger.info(f"   Очередь ордеров: {queues['orders']}")

            # Проверяем статус Signal Scheduler
            if orchestrator.signal_scheduler:
                scheduler_status = await orchestrator.signal_scheduler.get_status()
                active_symbols = sum(
                    1 for s in scheduler_status["symbols"].values() if s["active"]
                )
                logger.info(f"   Signal Scheduler: {active_symbols} активных символов")

                # Выводим последние сигналы
                for symbol, info in scheduler_status["symbols"].items():
                    if info.get("last_signal"):
                        last_signal = info["last_signal"]
                        if "signal" in last_signal:
                            signal = last_signal["signal"]
                            logger.info(
                                f"   📊 {symbol}: {signal.signal_type.value} "
                                f"(уверенность: {signal.confidence:.1f}%)"
                            )

            # Если есть обработанные сигналы - выходим раньше
            if metrics["signals_processed"] > 0:
                logger.info("\n✅ Сигналы обработаны!")
                break

        # 7. Финальный отчет
        logger.info("\n" + "=" * 80)
        logger.info("📊 ФИНАЛЬНЫЙ ОТЧЕТ")
        logger.info("=" * 80)

        final_status = orchestrator.trading_engine.get_status()
        final_metrics = final_status["metrics"]

        logger.info("\n🎯 Результаты тестирования:")
        logger.info(f"   ✅ Сигналов обработано: {final_metrics['signals_processed']}")
        logger.info(f"   ✅ Ордеров выполнено: {final_metrics['orders_executed']}")
        logger.info(f"   ✅ Активных позиций: {final_metrics['active_positions']}")
        logger.info(
            f"   ✅ Среднее время обработки: {final_metrics['processing_time_avg']:.3f}с"
        )
        logger.info(f"   ⚠️ Ошибок: {final_metrics['errors_count']}")

        if final_metrics["signals_processed"] > 0:
            logger.info("\n🎉 ТЕСТ УСПЕШНО ЗАВЕРШЕН! Поток ML -> Orders работает!")
        else:
            logger.warning("\n⚠️ Сигналы не были обработаны. Проверьте конфигурацию.")

    except Exception as e:
        logger.error(f"\n❌ Ошибка во время теста: {e}", exc_info=True)

    finally:
        # 8. Остановка системы
        logger.info("\n📋 Остановка системы...")
        if orchestrator:
            await orchestrator.shutdown()
        logger.info("✅ Система остановлена")

        logger.info("\n" + "=" * 80)
        logger.info("Тест завершен")
        logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_ml_to_orders_flow())
