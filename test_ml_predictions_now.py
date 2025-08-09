#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест ML предсказаний с исправленным FeatureEngineer
"""

import asyncio
from datetime import datetime

import numpy as np
import pandas as pd

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger(__name__)


async def test_ml_predictions():
    """Тест уникальности предсказаний"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Инициализируем ML Manager
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    # Создаем тестовые данные для BTC и ETH
    now = datetime.utcnow()
    dates = pd.date_range(end=now, periods=100, freq="15min")

    # BTC данные (цены около 55000)
    btc_data = pd.DataFrame(
        {
            "datetime": dates,
            "open": 55000 + np.random.randn(100) * 500,
            "high": 55500 + np.random.randn(100) * 500,
            "low": 54500 + np.random.randn(100) * 500,
            "close": 55000 + np.random.randn(100) * 500,
            "volume": 100 + np.random.exponential(50, 100),
            "turnover": 5000000 + np.random.exponential(1000000, 100),
            "symbol": "BTCUSDT",
        }
    )

    # ETH данные (цены около 2200)
    eth_data = pd.DataFrame(
        {
            "datetime": dates,
            "open": 2200 + np.random.randn(100) * 50,
            "high": 2250 + np.random.randn(100) * 50,
            "low": 2150 + np.random.randn(100) * 50,
            "close": 2200 + np.random.randn(100) * 50,
            "volume": 500 + np.random.exponential(200, 100),
            "turnover": 1000000 + np.random.exponential(500000, 100),
            "symbol": "ETHUSDT",
        }
    )

    # Убеждаемся что нет отрицательных значений
    for df in [btc_data, eth_data]:
        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            df[col] = np.maximum(df[col], 1.0)

    logger.info("🧪 Тестируем ML предсказания...")

    # Получаем предсказания
    btc_pred = await ml_manager.predict(btc_data)
    eth_pred = await ml_manager.predict(eth_data)

    logger.info("\n📊 Результаты предсказаний:")
    logger.info("\nBTC предсказание:")
    logger.info(f"  Signal: {btc_pred['signal_type']}")
    logger.info(f"  Returns 15m: {btc_pred['predictions']['returns_15m']:.6f}")
    logger.info(f"  Direction score: {btc_pred['predictions']['direction_score']:.3f}")

    logger.info("\nETH предсказание:")
    logger.info(f"  Signal: {eth_pred['signal_type']}")
    logger.info(f"  Returns 15m: {eth_pred['predictions']['returns_15m']:.6f}")
    logger.info(f"  Direction score: {eth_pred['predictions']['direction_score']:.3f}")

    # Проверяем различия
    returns_diff = abs(
        btc_pred["predictions"]["returns_15m"] - eth_pred["predictions"]["returns_15m"]
    )
    direction_diff = abs(
        btc_pred["predictions"]["direction_score"]
        - eth_pred["predictions"]["direction_score"]
    )

    logger.info("\n🔍 Анализ различий:")
    logger.info(f"  Разница returns_15m: {returns_diff:.6f}")
    logger.info(f"  Разница direction_score: {direction_diff:.3f}")

    if returns_diff < 1e-6 and direction_diff < 0.01:
        logger.error("❌ ПРОБЛЕМА: Предсказания идентичны!")
        return False
    else:
        logger.info("✅ УСПЕХ: Предсказания уникальны для разных символов!")
        return True


if __name__ == "__main__":
    asyncio.run(test_ml_predictions())
