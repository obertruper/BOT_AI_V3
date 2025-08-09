#!/usr/bin/env python3
"""
Тест feature engineering
"""

import time
from datetime import datetime

import numpy as np
import pandas as pd

from core.logger import setup_logger
from ml.logic.feature_engineering import FeatureEngineer

logger = setup_logger("test_fe")


def test_feature_engineering():
    """Тест генерации признаков"""
    try:
        # Создаем простые данные
        logger.info("Создаем тестовые данные...")
        dates = pd.date_range(end=datetime.now(), periods=100, freq="15min")

        data = pd.DataFrame(
            {
                "datetime": dates,
                "open": np.random.uniform(45000, 46000, 100),
                "high": np.random.uniform(45500, 46500, 100),
                "low": np.random.uniform(44500, 45500, 100),
                "close": np.random.uniform(45000, 46000, 100),
                "volume": np.random.uniform(100, 1000, 100),
                "symbol": "BTCUSDT",
            }
        )

        logger.info(f"Данные созданы: {data.shape}")
        logger.info(f"Колонки: {list(data.columns)}")

        # Инициализируем feature engineer
        logger.info("Инициализируем FeatureEngineer...")
        fe = FeatureEngineer({})

        # Генерируем признаки
        logger.info("Генерируем признаки...")
        start_time = time.time()

        features = fe.create_features(data)

        elapsed = time.time() - start_time
        logger.info(f"Признаки сгенерированы за {elapsed:.2f} сек")

        if isinstance(features, pd.DataFrame):
            logger.info(f"Результат - DataFrame: {features.shape}")
            numeric_cols = features.select_dtypes(include=[np.number]).columns
            feature_cols = [
                col
                for col in numeric_cols
                if not col.startswith(("future_", "direction_", "profit_"))
                and col not in ["id", "timestamp", "datetime", "symbol"]
            ]
            logger.info(f"Количество признаков: {len(feature_cols)}")
            logger.info(f"Первые 10 признаков: {list(feature_cols[:10])}")
        else:
            logger.info(f"Результат - ndarray: {features.shape}")

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)


if __name__ == "__main__":
    test_feature_engineering()
