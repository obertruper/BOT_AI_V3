#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки генерации ML сигналов
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor
from ml.signal_scheduler import SignalScheduler

logger = setup_logger(__name__)


async def test_signal_generation():
    """Тест генерации одного сигнала"""
    try:
        # Инициализация
        config_manager = ConfigManager()
        config = config_manager.get_config()

        logger.info("🚀 Инициализация компонентов...")

        # ML Manager
        ml_manager = MLManager(config)
        await ml_manager.initialize()
        logger.info("✅ ML Manager инициализирован")

        # Signal Processor
        signal_processor = MLSignalProcessor(
            ml_manager=ml_manager, config=config, config_manager=config_manager
        )
        await signal_processor.initialize()
        logger.info("✅ Signal Processor инициализирован")

        # Тестируем генерацию для одного символа
        symbol = "BTCUSDT"
        exchange = "bybit"

        logger.info(f"📊 Генерация сигнала для {symbol}...")

        # Генерируем сигнал
        signal = await signal_processor.process_realtime_signal(
            symbol=symbol, exchange=exchange
        )

        if signal:
            logger.info(f"✅ Сгенерирован {signal.signal_type.value} сигнал:")
            logger.info(f"   Уверенность: {signal.confidence:.2%}")
            logger.info(f"   Сила: {signal.strength:.2f}")
            logger.info(f"   Цена входа: ${signal.suggested_price:.2f}")
            logger.info(f"   Stop Loss: ${signal.suggested_stop_loss:.2f}")
            logger.info(f"   Take Profit: ${signal.suggested_take_profit:.2f}")
        else:
            logger.info("❌ Сигнал не сгенерирован (нет четкого направления)")

        # Проверяем метрики
        metrics = await signal_processor.get_metrics()
        logger.info("\n📈 Метрики процессора:")
        logger.info(f"   Обработано: {metrics['total_processed']}")
        logger.info(f"   Успешность: {metrics['success_rate']:.1%}")
        logger.info(f"   Сохранено: {metrics['save_rate']:.1%}")

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


async def test_scheduler():
    """Тест работы планировщика"""
    try:
        config_manager = ConfigManager()

        logger.info("🚀 Тест планировщика сигналов...")

        # Создаем планировщик
        scheduler = SignalScheduler(config_manager)

        # Инициализация
        await scheduler.initialize()
        logger.info("✅ Scheduler инициализирован")

        # Получаем статус
        status = await scheduler.get_status()
        logger.info("\n📊 Статус планировщика:")
        logger.info(f"   Включен: {status['enabled']}")
        logger.info(f"   Интервал: {status['interval_seconds']}с")
        logger.info(f"   Символов: {len(status['symbols'])}")

        # Запускаем на 2 минуты для теста
        logger.info("\n🔄 Запуск планировщика на 2 минуты...")
        await scheduler.start()

        # Ждем 2 минуты
        await asyncio.sleep(120)

        # Останавливаем
        await scheduler.stop()
        logger.info("✅ Планировщик остановлен")

        # Финальный статус
        final_status = await scheduler.get_status()
        logger.info("\n📊 Финальная статистика:")
        for symbol, data in final_status["symbols"].items():
            logger.info(
                f"   {symbol}: активен={data['active']}, ошибок={data['errors']}"
            )

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Основная функция"""
    logger.info("=" * 60)
    logger.info("🤖 Тест ML Signal Generation System")
    logger.info("=" * 60)

    # Тест 1: Генерация одного сигнала
    logger.info("\n📌 Тест 1: Генерация одного сигнала")
    await test_signal_generation()

    # Пауза между тестами
    await asyncio.sleep(5)

    # Тест 2: Работа планировщика
    logger.info("\n📌 Тест 2: Работа планировщика")
    await test_scheduler()

    logger.info("\n✅ Все тесты завершены")


if __name__ == "__main__":
    asyncio.run(main())
