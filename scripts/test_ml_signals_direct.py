#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Прямое тестирование генерации ML сигналов
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from data.data_loader import DataLoader
from database.connections import init_async_db
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger("test_ml_signals")


async def test_ml_signals():
    """Тестирование ML сигналов"""

    logger.info("🚀 Запуск теста ML сигналов...")

    # Инициализация БД
    await init_async_db()

    # Загрузка конфигурации
    config_manager = ConfigManager()
    await config_manager.initialize()
    config = config_manager._config

    # Инициализация ML Manager
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    logger.info("✅ ML Manager инициализирован")
    logger.info(f"📊 Модель: {ml_manager.get_model_info()}")

    # Инициализация ML Signal Processor
    signal_processor = MLSignalProcessor(ml_manager, config, config_manager)
    await signal_processor.initialize()

    logger.info("✅ Signal Processor инициализирован")

    # Инициализация Data Loader
    data_loader = DataLoader(config_manager)
    await data_loader.initialize()

    # Тестовый символ
    symbol = "BTCUSDT"
    exchange = "bybit"

    logger.info(f"\n🔍 Тестирование сигналов для {symbol}...")

    try:
        # Загружаем данные
        logger.info("📥 Загрузка OHLCV данных...")
        await data_loader.update_latest_data(
            symbols=[symbol], interval_minutes=15, exchange=exchange
        )

        # Даем данным загрузиться
        import time

        time.sleep(2)

        candles = True  # Данные загружены в БД

        if not candles:
            logger.error("❌ Не удалось загрузить данные")
            return

        logger.info("✅ Данные загружены в БД")

        # Генерируем сигнал
        logger.info("\n🤖 Генерация ML сигнала...")
        signal = await signal_processor.process_realtime_signal(
            symbol=symbol, exchange=exchange
        )

        if signal:
            logger.info(
                f"""
✅ СГЕНЕРИРОВАН {signal.signal_type.value.upper()} СИГНАЛ!
   Символ: {signal.symbol}
   Уверенность: {signal.confidence:.2%}
   Сила: {signal.strength:.2f}
   Stop Loss: {signal.suggested_stop_loss:.2f}
   Take Profit: {signal.suggested_take_profit:.2f}
   Стратегия: {signal.strategy_name}
"""
            )
        else:
            logger.info("⚪ Нет сигнала (нейтральная позиция)")

        # Тестируем несколько других символов
        test_symbols = ["ETHUSDT", "BNBUSDT", "SOLUSDT"]

        logger.info("\n🔄 Тестирование дополнительных символов...")

        signals = await signal_processor.generate_signals_for_symbols(
            symbols=test_symbols, exchange=exchange
        )

        logger.info("\n📊 Результаты:")
        logger.info(f"   Протестировано символов: {len(test_symbols)}")
        logger.info(f"   Сгенерировано сигналов: {len(signals)}")

        if signals:
            for sig in signals:
                logger.info(
                    f"   - {sig.symbol}: {sig.signal_type.value} "
                    f"(уверенность: {sig.confidence:.2%})"
                )

        # Статистика
        stats = await signal_processor.get_metrics()
        logger.info(
            f"""
📈 Статистика процессора:
   Обработано: {stats["total_processed"]}
   Успешность: {stats["success_rate"]:.1%}
   Сохранено: {stats["save_rate"]:.1%}
   Ошибок: {stats["error_rate"]:.1%}
"""
        )

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте: {e}", exc_info=True)

    finally:
        # Очистка
        await data_loader.cleanup()
        logger.info("\n✅ Тест завершен!")


if __name__ == "__main__":
    asyncio.run(test_ml_signals())
