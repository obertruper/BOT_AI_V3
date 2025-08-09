#!/usr/bin/env python3
"""
Быстрый тест ML для проверки предсказаний
"""

import asyncio
from datetime import datetime

import numpy as np
import pandas as pd

from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger("quick_ml_test")


async def test_predictions():
    """Тест с синтетическими данными"""
    try:
        # Создаем тестовые данные
        logger.info("Создаем тестовые данные...")
        dates = pd.date_range(end=datetime.now(), periods=200, freq="15min")

        # Генерируем тренд вверх для теста
        base_price = 45000
        trend = np.linspace(0, 1000, 200)  # Тренд вверх
        noise = np.random.normal(0, 50, 200)

        data = pd.DataFrame(
            {
                "datetime": dates,
                "open": base_price + trend + noise,
                "high": base_price + trend + noise + np.random.uniform(50, 100, 200),
                "low": base_price + trend + noise - np.random.uniform(50, 100, 200),
                "close": base_price + trend + noise + np.random.uniform(-20, 20, 200),
                "volume": np.random.uniform(100, 1000, 200),
                "symbol": "BTCUSDT",
            }
        )

        # Инициализируем ML Manager
        logger.info("Инициализируем ML Manager...")
        config = {"ml": {"model": {"device": "auto"}}}

        ml_manager = MLManager(config)
        await ml_manager.initialize()

        logger.info("Делаем предсказание...")
        prediction = await ml_manager.predict(data)

        # Результаты
        logger.info("=" * 50)
        logger.info(f"Сигнал: {prediction['signal_type']}")
        logger.info(f"Сила: {prediction['signal_strength']:.3f}")
        logger.info(f"Уверенность: {prediction['confidence']:.3f}")
        logger.info(f"Риск: {prediction['risk_level']}")
        logger.info("=" * 50)

        # Проверяем разнообразие
        raw_dirs = prediction["predictions"].get("raw_directions", [])
        if raw_dirs:
            unique_vals = len(set([round(d, 1) for d in raw_dirs]))
            logger.info(f"Уникальных значений: {unique_vals} из {len(raw_dirs)}")
            logger.info(f"Raw directions: {[f'{v:.2f}' for v in raw_dirs]}")

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_predictions())
