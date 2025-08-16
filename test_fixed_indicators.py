#!/usr/bin/env python3
"""
Тест исправленного расчета всех 240 индикаторов
"""

import asyncio

import numpy as np
import pandas as pd

from core.logger import setup_logger
from ml.config.features_240 import REQUIRED_FEATURES_240
from ml.logic.feature_engineering_v2 import FeatureEngineer

logger = setup_logger(__name__)


def generate_test_data(n_samples=300):
    """Генерирует тестовые OHLCV данные"""
    dates = pd.date_range(start="2024-01-01", periods=n_samples, freq="5T")

    # Генерируем реалистичные OHLCV данные
    np.random.seed(42)
    base_price = 50000
    returns = np.random.normal(0, 0.001, n_samples)
    prices = [base_price]

    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    prices = np.array(prices)

    # Создаем OHLCV
    df = pd.DataFrame(
        {
            "datetime": dates,
            "open": prices,
            "high": prices * (1 + np.random.uniform(0, 0.01, n_samples)),
            "low": prices * (1 - np.random.uniform(0, 0.01, n_samples)),
            "close": prices,
            "volume": np.random.uniform(100, 1000, n_samples),
            "symbol": "BTCUSDT",
        }
    )

    # Добавляем turnover
    df["turnover"] = df["close"] * df["volume"]

    # Оставляем datetime как колонку (требуется для FeatureEngineer)
    # df.set_index('datetime', inplace=True)

    return df


async def test_fixed_indicators():
    """Тестирует исправленный расчет индикаторов"""
    logger.info("🧪 Начинаем тест исправленных индикаторов...")

    # Генерируем тестовые данные
    test_data = generate_test_data(300)
    logger.info(f"📊 Сгенерированы тестовые данные: {len(test_data)} свечей")

    # Создаем FeatureEngineer с inference mode
    config = {"inference_mode": True}
    engineer = FeatureEngineer(config, inference_mode=True)

    # Рассчитываем признаки
    logger.info("🔧 Начинаем расчет признаков...")
    try:
        features_df = engineer.create_features(test_data, inference_mode=True)
        logger.info(f"✅ Признаки рассчитаны: {features_df.shape}")

        # Проверяем количество признаков
        feature_cols = [col for col in features_df.columns if col not in ["symbol", "datetime"]]
        logger.info(f"📈 Всего признаков: {len(feature_cols)}")

        # Проверяем наличие ключевых индикаторов
        key_indicators = [
            "rsi_5",
            "rsi_14",
            "sma_5",
            "sma_10",
            "ema_5",
            "ema_10",
            "macd_12_26",
            "atr_7",
            "atr_14",
        ]
        missing_key = []
        present_key = []

        for indicator in key_indicators:
            if indicator in feature_cols:
                present_key.append(indicator)
            else:
                missing_key.append(indicator)

        logger.info(f"✅ Присутствующие ключевые индикаторы ({len(present_key)}): {present_key}")
        if missing_key:
            logger.warning(
                f"❌ Отсутствующие ключевые индикаторы ({len(missing_key)}): {missing_key}"
            )

        # Проверяем REQUIRED_FEATURES_240
        available_required = []
        missing_required = []

        for feature in REQUIRED_FEATURES_240:
            if feature in feature_cols:
                available_required.append(feature)
            else:
                missing_required.append(feature)

        logger.info("📊 Статистика по REQUIRED_FEATURES_240:")
        logger.info(f"  ✅ Доступно: {len(available_required)}/240")
        logger.info(f"  ❌ Отсутствует: {len(missing_required)}/240")

        if missing_required:
            logger.warning(f"⚠️ Первые 10 отсутствующих: {missing_required[:10]}")

        # Проверяем NaN значения
        last_row = features_df.iloc[-1]
        nan_counts = {}
        total_nan = 0

        for col in feature_cols:
            if col in last_row and pd.isna(last_row[col]):
                nan_counts[col] = 1
                total_nan += 1

        logger.info(f"🧪 NaN значения в последней строке: {total_nan}/{len(feature_cols)}")
        if nan_counts:
            logger.warning(f"⚠️ Столбцы с NaN: {list(nan_counts.keys())[:10]}")

        # Проверяем дисперсию признаков
        non_zero_variance = 0
        zero_variance = []

        for col in feature_cols:
            if col in features_df.columns:
                col_var = features_df[col].var()
                if pd.isna(col_var) or col_var == 0:
                    zero_variance.append(col)
                else:
                    non_zero_variance += 1

        logger.info("📊 Дисперсия признаков:")
        logger.info(f"  ✅ С ненулевой дисперсией: {non_zero_variance}")
        logger.info(f"  ❌ С нулевой дисперсией: {len(zero_variance)}")

        if zero_variance:
            logger.warning(f"⚠️ Признаки с нулевой дисперсией: {zero_variance[:10]}")

        return {
            "total_features": len(feature_cols),
            "required_available": len(available_required),
            "required_missing": len(missing_required),
            "nan_count": total_nan,
            "non_zero_variance": non_zero_variance,
            "success": True,
        }

    except Exception as e:
        logger.error(f"❌ Ошибка при расчете признаков: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = asyncio.run(test_fixed_indicators())

    if result["success"]:
        print("\n" + "=" * 60)
        print("🎯 РЕЗУЛЬТАТЫ ТЕСТА ИСПРАВЛЕННЫХ ИНДИКАТОРОВ")
        print("=" * 60)
        print(f"📊 Всего признаков: {result['total_features']}")
        print(f"✅ REQUIRED_FEATURES_240 доступно: {result['required_available']}/240")
        print(f"❌ REQUIRED_FEATURES_240 отсутствует: {result['required_missing']}/240")
        print(f"🧪 NaN значений: {result['nan_count']}")
        print(f"📈 Признаков с ненулевой дисперсией: {result['non_zero_variance']}")

        if result["required_available"] == 240 and result["nan_count"] == 0:
            print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Система готова к работе.")
        else:
            print("\n⚠️ ТРЕБУЕТСЯ ДОРАБОТКА:")
            if result["required_available"] < 240:
                print(f"  - Добавить {240 - result['required_available']} недостающих признаков")
            if result["nan_count"] > 0:
                print(f"  - Убрать {result['nan_count']} NaN значений")
    else:
        print(f"\n❌ ТЕСТ НЕ ПРОЙДЕН: {result['error']}")
