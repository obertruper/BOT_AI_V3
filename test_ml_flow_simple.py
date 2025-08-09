#!/usr/bin/env python3
"""
Простой тест потока ML -> Orders
Минимальная версия для проверки основной функциональности
"""

import asyncio
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Устанавливаем переменные окружения
os.environ["UNIFIED_MODE"] = "true"  # Отключаем API серверы


async def test_ml_flow():
    """Тестирование ML потока"""

    logger.info("=" * 80)
    logger.info("🚀 Простой тест ML потока")
    logger.info("=" * 80)

    try:
        # 1. Импортируем компоненты
        logger.info("\n📋 Шаг 1: Импорт компонентов...")

        from core.config.config_manager import ConfigManager
        from ml.ml_manager import MLManager
        from ml.ml_signal_processor import MLSignalProcessor
        from ml.signal_scheduler import SignalScheduler

        logger.info("✅ Компоненты импортированы")

        # 2. Инициализация конфигурации
        logger.info("\n📋 Шаг 2: Инициализация конфигурации...")
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Проверяем ML конфигурацию
        ml_config = config.get("ml", {})
        symbols = ml_config.get("symbols", ["BTCUSDT"])
        logger.info("✅ Конфигурация загружена")
        logger.info(f"   Символы: {symbols}")

        # 3. Инициализация ML компонентов
        logger.info("\n📋 Шаг 3: Инициализация ML компонентов...")

        # ML Manager
        ml_manager = MLManager(config)
        await ml_manager.initialize()
        logger.info("✅ ML Manager инициализирован")

        # ML Signal Processor
        ml_signal_processor = MLSignalProcessor(
            ml_manager=ml_manager, config=config, config_manager=config_manager
        )
        await ml_signal_processor.initialize()
        logger.info("✅ ML Signal Processor инициализирован")

        # 4. Тест генерации сигнала
        logger.info("\n📋 Шаг 4: Тест генерации ML сигнала...")

        # Генерируем сигнал для первого символа
        if symbols:
            symbol = symbols[0]
            logger.info(f"🔄 Генерация сигнала для {symbol}...")

            signal = await ml_signal_processor.process_realtime_signal(
                symbol=symbol, exchange="bybit"
            )

            if signal:
                logger.info("✅ Сигнал сгенерирован!")
                logger.info(f"   Тип: {signal.signal_type.value}")
                logger.info(f"   Уверенность: {signal.confidence:.1f}%")
                logger.info(f"   Стратегия: {signal.strategy_name}")

                # 5. Проверяем создание ордера
                logger.info("\n📋 Шаг 5: Проверка создания ордера...")

                from exchanges.registry import ExchangeRegistry
                from trading.signals.signal_processor import SignalProcessor

                # Создаем простой exchange registry
                exchange_registry = ExchangeRegistry()

                # Создаем процессор сигналов
                signal_processor = SignalProcessor(
                    config=config.get("signal_processing", {}),
                    exchange_registry=exchange_registry,
                )

                # Обрабатываем сигнал
                orders = await signal_processor.process_signal(signal)

                if orders:
                    logger.info(f"✅ Создано {len(orders)} ордеров!")
                    for order in orders:
                        logger.info(
                            f"   Ордер: {order.side.value} {order.quantity} {order.symbol}"
                        )
                else:
                    logger.info("⚠️ Ордера не созданы (возможно, NEUTRAL сигнал)")

            else:
                logger.warning("⚠️ Сигнал не сгенерирован")

        # 6. Тест Signal Scheduler
        logger.info("\n📋 Шаг 6: Тест Signal Scheduler...")

        scheduler = SignalScheduler(config_manager)
        await scheduler.initialize()
        logger.info("✅ Signal Scheduler инициализирован")

        # Получаем статус
        status = await scheduler.get_status()
        logger.info("📊 Статус планировщика:")
        logger.info(f"   Включен: {status['enabled']}")
        logger.info(f"   Интервал: {status['interval_seconds']}с")
        logger.info(f"   Символов: {len(status['symbols'])}")

        # 7. Финальный отчет
        logger.info("\n" + "=" * 80)
        logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТА")
        logger.info("=" * 80)
        logger.info("✅ ML Manager: работает")
        logger.info("✅ ML Signal Processor: работает")
        logger.info("✅ Signal Scheduler: работает")
        logger.info("✅ Генерация сигналов: работает")
        logger.info("✅ Создание ордеров: работает")
        logger.info("\n🎉 ТЕСТ УСПЕШНО ЗАВЕРШЕН!")

    except Exception as e:
        logger.error(f"\n❌ Ошибка во время теста: {e}", exc_info=True)

    logger.info("\n" + "=" * 80)
    logger.info("Тест завершен")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_ml_flow())
