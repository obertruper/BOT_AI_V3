#!/usr/bin/env python3
"""
Прямой тест ML модели
"""

import asyncio
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yaml

from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger(__name__)


async def test_ml_direct():
    """Тестируем ML модель напрямую"""

    # Загружаем конфигурацию
    with open("config/ml/ml_config.yaml", "r") as f:
        ml_config = yaml.safe_load(f)

    # Инициализируем ML Manager
    ml_manager = MLManager(ml_config)
    await ml_manager.initialize()

    # Создаем тестовые данные - DataFrame с OHLCV
    data = []
    base_price = 100000
    now = datetime.now()

    for i in range(96):
        timestamp = now - timedelta(minutes=15 * (95 - i))
        price = base_price + np.random.randn() * 100

        data.append(
            {
                "datetime": timestamp,
                "open": price,
                "high": price + abs(np.random.randn() * 50),
                "low": price - abs(np.random.randn() * 50),
                "close": price + np.random.randn() * 30,
                "volume": 1000 + np.random.rand() * 500,
            }
        )

    df = pd.DataFrame(data)
    logger.info(f"Создано {len(df)} свечей для теста")

    try:
        # Делаем предсказание
        prediction = await ml_manager.predict(df)

        logger.info("\n✅ Предсказание получено!")
        logger.info(f"Тип: {type(prediction)}")
        logger.info(f"Содержимое: {prediction}")

        if isinstance(prediction, dict):
            logger.info("\nРезультаты ML предсказания:")
            logger.info(f"signal_type: {prediction.get('signal_type')}")
            logger.info(f"confidence: {prediction.get('confidence')}")
            logger.info(f"signal_strength: {prediction.get('signal_strength')}")
            logger.info(f"risk_level: {prediction.get('risk_level')}")

            if "predictions" in prediction:
                preds = prediction["predictions"]
                logger.info("\nДетали predictions:")
                for key, value in preds.items():
                    logger.info(f"  {key}: {value}")

        return prediction

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        return None


async def main():
    logger.info("\n" + "=" * 60)
    logger.info("Прямой тест ML модели")
    logger.info("=" * 60 + "\n")

    result = await test_ml_direct()

    if result is not None:
        logger.info("\n✅ ML модель работает корректно")
    else:
        logger.error("\n❌ Проблема с ML моделью")


if __name__ == "__main__":
    asyncio.run(main())
