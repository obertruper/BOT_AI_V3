#!/usr/bin/env python3
"""
Прямой тест feature engineering чтобы найти проблему
"""

import asyncio

import numpy as np
import pandas as pd
from sqlalchemy import and_, select

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from database.connections import get_async_db
from database.models.market_data import RawMarketData
from ml.logic.feature_engineering_v2 import FeatureEngineer

logger = setup_logger(__name__)


async def test_feature_engineering_with_real_data():
    """Тест feature engineering с реальными данными из БД"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Получаем данные из БД для BTCUSDT
    symbol = "BTCUSDT"

    async with get_async_db() as db:
        stmt = (
            select(RawMarketData)
            .where(
                and_(
                    RawMarketData.symbol == symbol,
                    RawMarketData.exchange == "bybit",
                    RawMarketData.interval_minutes == 15,
                )
            )
            .order_by(RawMarketData.datetime.desc())
            .limit(200)
        )

        result = await db.execute(stmt)
        data = result.scalars().all()

        logger.info(f"Загружено {len(data)} записей для {symbol}")

        if len(data) < 96:
            logger.error(f"Недостаточно данных: {len(data)} < 96")
            return

        # Преобразуем в DataFrame
        df = pd.DataFrame(
            [
                {
                    "datetime": d.datetime,
                    "symbol": d.symbol,
                    "open": float(d.open),
                    "high": float(d.high),
                    "low": float(d.low),
                    "close": float(d.close),
                    "volume": float(d.volume),
                    "turnover": float(d.turnover) if d.turnover else 0,
                }
                for d in reversed(data)  # Реверс для правильного порядка
            ]
        )

        logger.info(f"DataFrame создан: {df.shape}")
        logger.info(f"Колонки: {list(df.columns)}")
        logger.info(f"Первая строка:\n{df.iloc[0]}")
        logger.info(f"Последняя строка:\n{df.iloc[-1]}")

        # Тестируем feature engineering
        try:
            fe = FeatureEngineer(config)
            logger.info("\nЗапускаем create_features...")

            features = fe.create_features(df)

            logger.info("\nРезультат:")
            logger.info(f"  Тип: {type(features)}")
            if isinstance(features, np.ndarray):
                logger.info(f"  Форма: {features.shape}")
                logger.info(
                    f"  Первые 10 значений: {features[:10] if features.ndim == 1 else features[0, :10]}"
                )
                logger.info(f"  Содержит NaN: {np.isnan(features).any()}")
                logger.info(f"  Содержит Inf: {np.isinf(features).any()}")
            elif isinstance(features, pd.DataFrame):
                logger.info(f"  Форма: {features.shape}")
                logger.info(f"  Колонки: {list(features.columns)[:10]}...")
                logger.info(f"  Содержит NaN: {features.isna().any().any()}")

        except Exception as e:
            logger.error(f"Ошибка в feature engineering: {e}", exc_info=True)


async def test_simple_feature_engineering():
    """Простой тест с минимальными данными"""

    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Создаем простые тестовые данные
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

    logger.info("\nТестовые данные:")
    logger.info(f"  Форма: {df.shape}")
    logger.info(f"  Типы данных:\n{df.dtypes}")

    try:
        fe = FeatureEngineer(config)
        features = fe.create_features(df)

        logger.info("\nРезультат create_features:")
        logger.info(f"  Возвращен тип: {type(features)}")

        if hasattr(features, "shape"):
            logger.info(f"  Форма: {features.shape}")

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)


async def main():
    """Основная функция"""

    logger.info("\n" + "=" * 80)
    logger.info("🧪 Тест Feature Engineering")
    logger.info("=" * 80 + "\n")

    # Простой тест
    logger.info("1. Простой тест с синтетическими данными")
    await test_simple_feature_engineering()

    # Тест с реальными данными
    logger.info("\n2. Тест с реальными данными из БД")
    await test_feature_engineering_with_real_data()


if __name__ == "__main__":
    asyncio.run(main())
