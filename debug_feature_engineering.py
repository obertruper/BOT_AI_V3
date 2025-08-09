#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест FeatureEngineer с разными символами для проверки уникальности
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


async def test_feature_engineering():
    """Тестирует генерацию признаков для разных символов"""
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Создаем тестовые данные для BTCUSDT и ETHUSDT
    btc_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=100, freq="15min"),
            "open": 40000 + np.random.randn(100) * 1000,
            "high": 40500 + np.random.randn(100) * 1000,
            "low": 39500 + np.random.randn(100) * 1000,
            "close": 40000 + np.random.randn(100) * 1000,
            "volume": 1000 + np.random.randn(100) * 100,
            "turnover": 40000000 + np.random.randn(100) * 1000000,
            "symbol": "BTCUSDT",
        }
    )

    eth_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=100, freq="15min"),
            "open": 2500 + np.random.randn(100) * 200,
            "high": 2600 + np.random.randn(100) * 200,
            "low": 2400 + np.random.randn(100) * 200,
            "close": 2500 + np.random.randn(100) * 200,
            "volume": 2000 + np.random.randn(100) * 200,
            "turnover": 5000000 + np.random.randn(100) * 500000,
            "symbol": "ETHUSDT",
        }
    )

    # Убеждаемся что цены не отрицательные
    for df in [btc_data, eth_data]:
        for col in ["open", "high", "low", "close"]:
            df[col] = np.abs(df[col])
        df["volume"] = np.abs(df["volume"])
        df["turnover"] = np.abs(df["turnover"])

    logger.info("📊 Создан тестовые данные:")
    logger.info(
        f"BTC: цены от {btc_data['close'].min():.0f} до {btc_data['close'].max():.0f}"
    )
    logger.info(
        f"ETH: цены от {eth_data['close'].min():.0f} до {eth_data['close'].max():.0f}"
    )

    # Инициализируем FeatureEngineer
    feature_engineer = FeatureEngineer(config)

    # Генерируем признаки
    logger.info("\n🔄 Генерация признаков...")

    btc_features = feature_engineer.create_features(btc_data)
    logger.info(
        f"BTC признаки: shape={btc_features.shape}, min={btc_features.min():.6f}, max={btc_features.max():.6f}"
    )

    eth_features = feature_engineer.create_features(eth_data)
    logger.info(
        f"ETH признаки: shape={eth_features.shape}, min={eth_features.min():.6f}, max={eth_features.max():.6f}"
    )

    # Анализ уникальности
    logger.info("\n📋 Анализ уникальности:")

    # Сравниваем статистики
    btc_mean = np.mean(btc_features, axis=0)
    eth_mean = np.mean(eth_features, axis=0)

    btc_std = np.std(btc_features, axis=0)
    eth_std = np.std(eth_features, axis=0)

    # Количество признаков с нулевой дисперсией
    btc_zero_var = np.sum(btc_std < 1e-8)
    eth_zero_var = np.sum(eth_std < 1e-8)

    logger.info(
        f"BTC: признаков с нулевой дисперсией: {btc_zero_var}/{btc_features.shape[1]}"
    )
    logger.info(
        f"ETH: признаков с нулевой дисперсией: {eth_zero_var}/{eth_features.shape[1]}"
    )

    # Корреляция между признаками разных символов
    if btc_features.shape == eth_features.shape:
        correlations = []
        for i in range(btc_features.shape[1]):
            if btc_std[i] > 1e-8 and eth_std[i] > 1e-8:
                corr = np.corrcoef(btc_features[:, i], eth_features[:, i])[0, 1]
                if not np.isnan(corr):
                    correlations.append(corr)

        if correlations:
            avg_corr = np.mean(correlations)
            logger.info(f"Средняя корреляция между признаками BTC-ETH: {avg_corr:.6f}")
            logger.info(
                f"Высоко коррелированных признаков (>0.9): {np.sum(np.array(correlations) > 0.9)}"
            )
        else:
            logger.warning("⚠️ Нет валидных корреляций для вычисления")

    # Проверяем различия в первых 10 признаках
    logger.info("\n🔍 Первые 10 признаков (последняя временная точка):")
    logger.info(f"BTC: {btc_features[-1, :10]}")
    logger.info(f"ETH: {eth_features[-1, :10]}")
    logger.info(f"Разности: {btc_features[-1, :10] - eth_features[-1, :10]}")

    # Проверяем проблему с клиппингом
    btc_clipped = np.sum((btc_features == -10) | (btc_features == 10))
    eth_clipped = np.sum((eth_features == -10) | (eth_features == 10))

    logger.info("\n⚠️ Клиппированные значения:")
    logger.info(f"BTC: {btc_clipped} значений на границах [-10, 10]")
    logger.info(f"ETH: {eth_clipped} значений на границах [-10, 10]")

    if btc_clipped > 0 or eth_clipped > 0:
        logger.error("❌ ПРОБЛЕМА: Обнаружен чрезмерный клиппинг признаков!")
        logger.error("   Это может приводить к потере уникальности между символами")

    return btc_features, eth_features


if __name__ == "__main__":
    asyncio.run(test_feature_engineering())
