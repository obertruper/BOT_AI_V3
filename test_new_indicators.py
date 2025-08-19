#!/usr/bin/env python3
"""
Тестирование новых индикаторов и feature engineering
"""

import asyncio
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from core.logger import setup_logger
from ml.logic.archive_old_versions.feature_engineering_v2 import FeatureEngineer
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

logger = setup_logger(__name__)


async def test_new_indicators():
    """Тест новых индикаторов"""

    # Создаем тестовые данные
    periods = 500
    dates = pd.date_range(end=datetime.now(UTC), periods=periods, freq="15min")

    # Симулируем ценовые данные с трендом и шумом
    trend = np.linspace(100000, 102000, periods)
    noise = np.random.normal(0, 200, periods)
    prices = trend + noise

    df = pd.DataFrame(
        {
            "datetime": dates,
            "symbol": "BTCUSDT",
            "open": prices * 0.999,
            "high": prices * 1.002,
            "low": prices * 0.998,
            "close": prices,
            "volume": np.random.uniform(100, 500, periods) * 1e6,
            "turnover": prices * np.random.uniform(100, 500, periods) * 1e6,
        }
    )

    logger.info("=" * 50)
    logger.info("🔬 ТЕСТИРОВАНИЕ НОВЫХ ИНДИКАТОРОВ")
    logger.info("=" * 50)

    # 1. Тест FeatureEngineer
    logger.info("\n📊 1. Тестирование FeatureEngineer")
    fe = FeatureEngineer({})

    # Создаем признаки
    features_df = fe.create_features(df.copy())

    # Проверяем новые индикаторы
    new_indicators = [
        "hurst_exponent",
        "fractal_dimension",
        "efficiency_ratio",
        "ichimoku_tenkan",
        "ichimoku_kijun",
        "ichimoku_cloud_thickness",
        "keltner_upper_20",
        "keltner_position_20",
        "donchian_upper_20",
        "donchian_position_20",
        "mfi_14",
        "cci_14",
        "williams_r_14",
        "adx_14",
        "obv",
        "realized_vol_1h",
        "garch_vol",
        "return_entropy",
        "returns_ac_1",
        "returns_ac_5",
        "returns_ac_10",
        "returns_ac_20",
        "price_jump",
        "jump_intensity",
        "vol_clustering",
        "efficiency_volatility",
        "microstructure_noise",
    ]

    logger.info("\n✅ Проверка наличия новых индикаторов:")
    for indicator in new_indicators:
        if indicator in features_df.columns:
            value = features_df[indicator].iloc[-1]
            if pd.notna(value):
                logger.info(f"  ✓ {indicator}: {value:.4f}")
            else:
                logger.warning(f"  ⚠ {indicator}: NaN")
        else:
            logger.error(f"  ✗ {indicator}: НЕ НАЙДЕН")

    # 2. Тест RealTimeIndicatorCalculator
    logger.info("\n📊 2. Тестирование RealTimeIndicatorCalculator")
    calc = RealTimeIndicatorCalculator()

    # Рассчитываем индикаторы
    indicators = await calc.calculate_indicators(
        "BTCUSDT", df.set_index("datetime"), save_to_db=False
    )

    if indicators:
        logger.info("\n✅ Структура результата:")
        for key in indicators.keys():
            if isinstance(indicators[key], dict):
                logger.info(f"  {key}: {len(indicators[key])} элементов")
            else:
                logger.info(f"  {key}: {type(indicators[key])}")

        # Проверяем ML features
        if "ml_features" in indicators:
            ml_features = indicators["ml_features"]
            logger.info(f"\n📊 ML признаков: {len(ml_features)}")

            # Проверяем наличие новых ML признаков
            ml_indicators = [
                "hurst_exponent",
                "fractal_dimension",
                "efficiency_ratio",
                "return_entropy",
                "vol_clustering",
                "microstructure_noise",
            ]

            for ind in ml_indicators:
                found = any(ind in key for key in ml_features.keys())
                if found:
                    matching_keys = [k for k in ml_features.keys() if ind in k]
                    logger.info(f"  ✓ {ind} найден в: {matching_keys[0][:50]}...")
                else:
                    logger.warning(f"  ⚠ {ind} не найден в ML features")

    # 3. Проверка качества данных
    logger.info("\n📊 3. Проверка качества данных")

    # Проверяем NaN значения
    nan_counts = features_df.isnull().sum()
    high_nan_cols = nan_counts[nan_counts > len(features_df) * 0.5]

    if len(high_nan_cols) > 0:
        logger.warning("\n⚠ Колонки с >50% NaN значений:")
        for col in high_nan_cols.index[:10]:
            logger.warning(
                f"  {col}: {nan_counts[col]}/{len(features_df)} ({nan_counts[col] / len(features_df) * 100:.1f}%)"
            )
    else:
        logger.info("✅ Все колонки имеют <50% NaN значений")

    # Проверяем бесконечные значения
    inf_counts = np.isinf(features_df.select_dtypes(include=[np.number])).sum()
    inf_cols = inf_counts[inf_counts > 0]

    if len(inf_cols) > 0:
        logger.warning("\n⚠ Колонки с бесконечными значениями:")
        for col in inf_cols.index[:10]:
            logger.warning(f"  {col}: {inf_counts[col]} inf значений")
    else:
        logger.info("✅ Нет колонок с бесконечными значениями")

    # 4. Проверка ML input
    logger.info("\n📊 4. Тест подготовки ML входа")

    try:
        ml_input, metadata = await calc.prepare_ml_input("BTCUSDT", df.set_index("datetime"))
        logger.info(f"✅ ML input shape: {ml_input.shape}")
        logger.info(f"   Metadata: {metadata}")

        # Проверяем дисперсию
        feature_std = np.std(ml_input[0], axis=0)
        zero_std_features = np.sum(feature_std < 1e-6)
        logger.info(f"   Признаков с нулевой дисперсией: {zero_std_features}/{ml_input.shape[2]}")

        if zero_std_features > ml_input.shape[2] * 0.3:
            logger.warning("⚠ Слишком много признаков с нулевой дисперсией!")

    except Exception as e:
        logger.error(f"❌ Ошибка подготовки ML входа: {e}")

    logger.info("\n" + "=" * 50)
    logger.info("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_new_indicators())
