#!/usr/bin/env python3
"""
Тест feature engineering в изоляции
"""

from datetime import datetime

import numpy as np
import pandas as pd

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.logic.feature_engineering_v2 import FeatureEngineer

logger = setup_logger(__name__)


async def test_simple_features():
    """Тест с минимальными данными"""

    config = ConfigManager().get_config()

    # Создаем минимальные данные
    dates = pd.date_range(start="2024-01-01", periods=100, freq="15min")

    df = pd.DataFrame(
        {
            "datetime": dates,
            "symbol": "BTCUSDT",
            "open": 42000 + np.random.randn(100) * 100,
            "high": 42100 + np.random.randn(100) * 100,
            "low": 41900 + np.random.randn(100) * 100,
            "close": 42000 + np.random.randn(100) * 100,
            "volume": 1000 + np.random.randn(100) * 10,
            "turnover": 42000000 + np.random.randn(100) * 100000,
        }
    )

    # Убедимся что high >= open,close и low <= open,close
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)

    logger.info(f"Входные данные: {df.shape}")
    logger.info(f"Колонки: {list(df.columns)}")

    try:
        fe = FeatureEngineer(config)
        fe.disable_progress = True  # Отключаем прогресс

        logger.info("Вызываем create_features...")
        start_time = datetime.now()

        features = fe.create_features(df)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"create_features завершен за {elapsed:.2f} сек")

        logger.info(f"Результат: {type(features)}")
        logger.info(f"Форма: {features.shape}")

        if isinstance(features, pd.DataFrame):
            logger.info(
                f"Числовых колонок: {len(features.select_dtypes(include=[np.number]).columns)}"
            )
            logger.info(f"Примеры колонок: {list(features.columns)[:10]}")

            # Проверяем на NaN
            nan_cols = features.isna().sum()
            nan_cols = nan_cols[nan_cols > 0]
            if len(nan_cols) > 0:
                logger.warning(f"Колонки с NaN: {dict(nan_cols)}")
            else:
                logger.info("✅ Нет NaN значений")

        return features

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        return None


async def main():
    logger.info("\n" + "=" * 60)
    logger.info("Тест Feature Engineering")
    logger.info("=" * 60 + "\n")

    result = await test_simple_features()

    if result is not None:
        logger.info("\n✅ Тест пройден успешно")
    else:
        logger.error("\n❌ Тест провален")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
