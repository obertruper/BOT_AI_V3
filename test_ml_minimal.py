#!/usr/bin/env python3
"""
Минимальный тест для отладки ML предсказаний
"""

import asyncio

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger(__name__)


async def test_one_symbol():
    """Тестируем один символ детально"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Инициализируем компоненты
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    signal_processor = MLSignalProcessor(
        ml_manager=ml_manager, config=config, config_manager=config_manager
    )
    await signal_processor.initialize()

    # Тестируем BTCUSDT
    symbol = "BTCUSDT"

    logger.info(f"\n{'=' * 60}")
    logger.info(f"Тестируем {symbol}")
    logger.info(f"{'=' * 60}\n")

    # Пробуем сгенерировать сигнал
    try:
        signal = await signal_processor.process_realtime_signal(
            symbol=symbol, exchange="bybit"
        )

        if signal:
            logger.info("✅ Сигнал сгенерирован!")
            logger.info(f"   Тип: {signal.signal_type.value}")
            logger.info(f"   Уверенность: {signal.confidence:.2%}")
            logger.info(f"   Сила: {signal.strength:.2f}")

            # Смотрим сырые предсказания
            raw_pred = signal.extra_data.get("raw_prediction", {})
            if raw_pred:
                predictions = raw_pred.get("predictions", [])
                if len(predictions) >= 8:
                    logger.info("\n   Направления:")
                    logger.info(f"   15m: {predictions[4]}")
                    logger.info(f"   1h: {predictions[5]}")
                    logger.info(f"   4h: {predictions[6]}")
                    logger.info(f"   12h: {predictions[7]}")
        else:
            logger.warning("❌ Сигнал не сгенерирован")

            # Проверяем пороги
            logger.info(
                f"\n   Минимальная уверенность: {signal_processor.min_confidence}"
            )
            logger.info(f"   Минимальная сила: {signal_processor.min_signal_strength}")

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)


async def main():
    """Основная функция"""
    await test_one_symbol()


if __name__ == "__main__":
    asyncio.run(main())
