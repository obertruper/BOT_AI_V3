#!/usr/bin/env python3
"""
Быстрый тест ML системы генерации сигналов
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневой каталог в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor
from ml.signal_scheduler import SignalScheduler

logger = setup_logger(__name__)


async def test_ml_signal_generation():
    """Быстрый тест генерации ML сигналов"""

    logger.info("🧪 Начинаем тест ML генерации сигналов...")

    try:
        # Инициализируем компоненты
        config_manager = ConfigManager()
        config = config_manager.get_config()

        # Проверяем что ML включен
        ml_config = config.get("ml", {})
        logger.info(f"ML конфигурация: enabled={ml_config.get('enabled', False)}")

        if not ml_config.get("enabled", False):
            logger.error("ML система отключена в конфигурации")
            logger.info("Включаем ML для теста...")
            if "ml" not in config:
                config["ml"] = {}
            config["ml"]["enabled"] = True

        logger.info("✅ ML система включена в конфигурации")

        # Инициализируем ML Manager
        logger.info("Инициализация ML Manager...")
        ml_manager = MLManager(config)
        await ml_manager.initialize()
        logger.info("✅ ML Manager инициализирован")

        # Инициализируем Signal Processor
        logger.info("Инициализация ML Signal Processor...")
        signal_processor = MLSignalProcessor(
            ml_manager=ml_manager, config=config, config_manager=config_manager
        )
        await signal_processor.initialize()
        logger.info("✅ ML Signal Processor инициализирован")

        # Тестируем генерацию сигнала для BTCUSDT
        test_symbol = "BTCUSDT"
        logger.info(f"🔄 Тест генерации сигнала для {test_symbol}...")

        signal = await signal_processor.process_realtime_signal(
            symbol=test_symbol, exchange="bybit"
        )

        if signal:
            logger.info("✅ Сигнал успешно сгенерирован:")
            logger.info(f"   Символ: {signal.symbol}")
            logger.info(f"   Тип: {signal.signal_type.value}")
            logger.info(f"   Уверенность: {signal.confidence:.2f}")
            logger.info(f"   Сила: {signal.strength:.2f}")

            # Проверяем валидацию
            is_valid = await signal_processor.validate_signal(signal)
            logger.info(f"   Валидность: {'✅ Да' if is_valid else '❌ Нет'}")

        else:
            logger.warning(f"⚠️ Сигнал для {test_symbol} не сгенерирован")

        # Получаем статистику
        stats = await signal_processor.get_metrics()
        logger.info("📊 Статистика процессора:")
        for key, value in stats.items():
            logger.info(f"   {key}: {value}")

        # Завершаем работу процессора
        await signal_processor.shutdown()

        logger.info("✅ Тест ML генерации сигналов завершен успешно")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте ML сигналов: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


async def test_signal_scheduler():
    """Тест SignalScheduler"""

    logger.info("🧪 Тест Signal Scheduler...")

    try:
        # Инициализируем планировщик
        scheduler = SignalScheduler()
        await scheduler.initialize()

        # Получаем статус
        status = await scheduler.get_status()
        logger.info("📊 Статус планировщика:")
        logger.info(f"   Запущен: {status['running']}")
        logger.info(f"   Включен: {status['enabled']}")
        logger.info(f"   Интервал: {status['interval_seconds']}с")
        logger.info(f"   Символов: {len(status['symbols'])}")

        # Тестовая генерация для одного символа
        test_symbol = "BTCUSDT"
        logger.info(f"🔄 Тест генерации для {test_symbol}...")

        signal = await scheduler._generate_signal(test_symbol)

        if signal:
            logger.info("✅ Сигнал от планировщика:")
            logger.info(f"   Тип: {signal.signal_type.value}")
            logger.info(f"   Уверенность: {signal.confidence:.2f}")
        else:
            logger.warning("⚠️ Сигнал от планировщика не сгенерирован")

        # Завершаем
        await scheduler.stop()

        logger.info("✅ Тест Signal Scheduler завершен")
        return True

    except Exception as e:
        logger.error(f"❌ Ошибка в тесте планировщика: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


async def main():
    """Основная функция тестирования"""

    logger.info("🚀 Запуск тестов ML системы")

    # Тест 1: Генерация сигналов
    test1_result = await test_ml_signal_generation()

    # Тест 2: Планировщик
    test2_result = await test_signal_scheduler()

    # Итоговый результат
    if test1_result and test2_result:
        logger.info("🎉 Все тесты ML системы прошли успешно!")
        return True
    else:
        logger.error("❌ Некоторые тесты не прошли")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
