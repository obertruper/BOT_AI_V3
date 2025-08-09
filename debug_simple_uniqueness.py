#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест уникальности признаков
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


async def test_simple_uniqueness():
    """Простой тест уникальности с синтетическими данными"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    logger.info("🧪 Тест уникальности с синтетическими данными...")

    # Создаем СИЛЬНО различающиеся данные
    np.random.seed(42)  # Фиксированный seed для воспроизводимости

    # BTC: цены около 40000, высокая волатильность
    btc_base_price = 40000
    btc_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=100, freq="15min"),
            "open": btc_base_price + np.random.randn(100) * 2000,  # Волатильность 2000
            "high": btc_base_price + 1000 + np.random.randn(100) * 2000,
            "low": btc_base_price - 1000 + np.random.randn(100) * 2000,
            "close": btc_base_price + np.random.randn(100) * 2000,
            "volume": 100
            + np.random.exponential(50, 100),  # Экспоненциальное распределение
            "turnover": 1000000 + np.random.exponential(500000, 100),
            "symbol": "BTCUSDT",
        }
    )

    # ETH: цены около 2500, совсем другая динамика
    eth_base_price = 2500
    eth_data = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=100, freq="15min"),
            "open": eth_base_price + np.random.randn(100) * 100,  # Волатильность 100
            "high": eth_base_price + 50 + np.random.randn(100) * 100,
            "low": eth_base_price - 50 + np.random.randn(100) * 100,
            "close": eth_base_price + np.random.randn(100) * 100,
            "volume": 500 + np.random.exponential(200, 100),  # Другое распределение
            "turnover": 200000 + np.random.exponential(100000, 100),
            "symbol": "ETHUSDT",
        }
    )

    # Убеждаемся что нет отрицательных значений
    for df, name in [(btc_data, "BTC"), (eth_data, "ETH")]:
        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            df[col] = np.maximum(df[col], 1.0)  # Минимум 1

        logger.info(f"{name} статистика:")
        logger.info(
            f"  Close: mean={df['close'].mean():.2f}, std={df['close'].std():.2f}"
        )
        logger.info(
            f"  Volume: mean={df['volume'].mean():.2f}, std={df['volume'].std():.2f}"
        )

    # Генерируем признаки
    feature_engineer = FeatureEngineer(config)

    btc_features = feature_engineer.create_features(btc_data)
    eth_features = feature_engineer.create_features(eth_data)

    logger.info("\n📊 Результаты:")
    logger.info(
        f"BTC features: shape={btc_features.shape}, mean={btc_features.mean():.6f}, std={btc_features.std():.6f}"
    )
    logger.info(
        f"ETH features: shape={eth_features.shape}, mean={eth_features.mean():.6f}, std={eth_features.std():.6f}"
    )

    # Детальный анализ уникальности
    if btc_features.shape == eth_features.shape:
        # Проверяем дисперсии
        btc_std = np.std(btc_features, axis=0)
        eth_std = np.std(eth_features, axis=0)

        btc_zero_var = np.sum(btc_std < 1e-8)
        eth_zero_var = np.sum(eth_std < 1e-8)

        logger.info("\n🔍 Анализ дисперсий:")
        logger.info(
            f"BTC zero variance features: {btc_zero_var}/{btc_features.shape[1]}"
        )
        logger.info(
            f"ETH zero variance features: {eth_zero_var}/{eth_features.shape[1]}"
        )

        # Проверяем различия между символами
        feature_differences = []
        for i in range(btc_features.shape[1]):
            if btc_std[i] > 1e-8 and eth_std[i] > 1e-8:
                # Сравниваем средние значения признаков
                btc_mean = np.mean(btc_features[:, i])
                eth_mean = np.mean(eth_features[:, i])
                diff = abs(btc_mean - eth_mean)
                feature_differences.append(diff)

        if feature_differences:
            avg_difference = np.mean(feature_differences)
            max_difference = np.max(feature_differences)
            min_difference = np.min(feature_differences)

            logger.info("\n📈 Различия между символами:")
            logger.info(f"Средняя разность признаков: {avg_difference:.6f}")
            logger.info(f"Максимальная разность: {max_difference:.6f}")
            logger.info(f"Минимальная разность: {min_difference:.6f}")

            if avg_difference < 0.01:
                logger.error("❌ ПРОБЛЕМА: Признаки слишком похожи между символами!")
                return False
            else:
                logger.info("✅ Признаки достаточно различны между символами")
                return True
        else:
            logger.error("❌ Нет валидных признаков для сравнения")
            return False
    else:
        logger.error("❌ Разные формы массивов признаков")
        return False


if __name__ == "__main__":
    asyncio.run(test_simple_uniqueness())
