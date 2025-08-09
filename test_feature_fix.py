#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест исправления FeatureEngineer
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.logic.feature_engineering import FeatureEngineer

logger = setup_logger(__name__)


async def test_feature_uniqueness():
    """Тест уникальности признаков после исправления"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    logger.info("🧪 Тест исправления FeatureEngineer...")

    # Создаем сильно различающиеся данные
    np.random.seed(42)

    # BTC: цены около 40000
    btc_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=100, freq="15min"),
            "open": 40000 + np.random.randn(100) * 2000,
            "high": 41000 + np.random.randn(100) * 2000,
            "low": 39000 + np.random.randn(100) * 2000,
            "close": 40000 + np.random.randn(100) * 2000,
            "volume": 100 + np.random.exponential(50, 100),
            "turnover": 1000000 + np.random.exponential(500000, 100),
            "symbol": "BTCUSDT",
        }
    )

    # ETH: цены около 2500
    eth_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=100, freq="15min"),
            "open": 2500 + np.random.randn(100) * 100,
            "high": 2550 + np.random.randn(100) * 100,
            "low": 2450 + np.random.randn(100) * 100,
            "close": 2500 + np.random.randn(100) * 100,
            "volume": 500 + np.random.exponential(200, 100),
            "turnover": 200000 + np.random.exponential(100000, 100),
            "symbol": "ETHUSDT",
        }
    )

    # Убеждаемся что нет отрицательных значений
    for df in [btc_data, eth_data]:
        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            df[col] = np.maximum(df[col], 1.0)

    # Генерируем признаки
    feature_engineer = FeatureEngineer(config)

    logger.info("\n📊 Генерируем признаки для BTC...")
    btc_features = feature_engineer.create_features(btc_data)

    logger.info("\n📊 Генерируем признаки для ETH...")
    eth_features = feature_engineer.create_features(eth_data)

    # Анализ результатов
    logger.info("\n🔍 Анализ результатов:")
    logger.info(f"BTC features: shape={btc_features.shape}")
    logger.info(f"ETH features: shape={eth_features.shape}")

    # Берем последнюю строку (самые свежие признаки)
    if isinstance(btc_features, pd.DataFrame):
        btc_last = btc_features.iloc[-1].values
        eth_last = eth_features.iloc[-1].values
    else:
        btc_last = btc_features[-1]
        eth_last = eth_features[-1]

    # Проверяем различия
    differences = np.abs(btc_last - eth_last)
    avg_diff = np.mean(differences)
    max_diff = np.max(differences)
    num_identical = np.sum(differences < 1e-10)

    logger.info("\n📈 Различия между BTC и ETH признаками:")
    logger.info(f"   Средняя разность: {avg_diff:.6f}")
    logger.info(f"   Максимальная разность: {max_diff:.6f}")
    logger.info(f"   Идентичных признаков: {num_identical}/{len(btc_last)}")

    # Первые 10 признаков для сравнения
    logger.info("\n🔍 Первые 10 признаков:")
    logger.info(f"   BTC: {btc_last[:10]}")
    logger.info(f"   ETH: {eth_last[:10]}")

    if avg_diff < 0.01 or num_identical > len(btc_last) * 0.5:
        logger.error("❌ ПРОБЛЕМА: Признаки слишком похожи!")
        return False
    else:
        logger.info("✅ УСПЕХ: Признаки различны для разных символов!")
        return True


if __name__ == "__main__":
    asyncio.run(test_feature_uniqueness())
