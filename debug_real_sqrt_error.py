#!/usr/bin/env python3
"""
Тест реального воспроизведения ошибки sqrt в ML pipeline
"""

import asyncio
import traceback

import numpy as np
import pandas as pd

from core.logger import setup_logger

# Импортируем реальные компоненты
from ml.logic.archive_old_versions.feature_engineering_v2 import FeatureEngineer

logger = setup_logger(__name__)


async def test_real_sqrt_error():
    """Тестируем реальный pipeline, который дает ошибку sqrt"""

    print("🔍 Тестируем реальный ML pipeline с FeatureEngineer...")

    try:
        # Создаем реальные тестовые данные как в системе
        dates = pd.date_range(start="2024-01-01", periods=500, freq="15min")

        np.random.seed(42)
        close_prices = 50000 + np.cumsum(np.random.randn(500) * 100)

        df = pd.DataFrame(
            {
                "datetime": dates,
                "open": close_prices * (1 + np.random.randn(500) * 0.001),
                "high": close_prices * (1 + np.abs(np.random.randn(500)) * 0.002),
                "low": close_prices * (1 - np.abs(np.random.randn(500)) * 0.002),
                "close": close_prices,
                "volume": np.random.rand(500) * 1000000,
                "turnover": np.random.rand(500) * 50000000,
                "symbol": "BTCUSDT",
            }
        )

        df.set_index("datetime", inplace=True)
        print(f"✅ Создан тестовый DataFrame: {df.shape}")

        # Создаем FeatureEngineer как в реальной системе
        config = {"inference_mode": True, "disable_progress": False}

        feature_engineer = FeatureEngineer(config, inference_mode=True)
        print("✅ FeatureEngineer создан")

        # Пытаемся сгенерировать признаки
        print("🚀 Запускаем generate_features...")

        features_result = feature_engineer.generate_features(df)

        print(f"✅ Признаки сгенерированы: {type(features_result)}")

        if isinstance(features_result, pd.DataFrame):
            print(f"📊 Shape: {features_result.shape}")
            print(f"📊 Columns: {len(features_result.columns)}")
            print(f"📊 NaN count: {features_result.isna().sum().sum()}")
        elif isinstance(features_result, np.ndarray):
            print(f"📊 Array shape: {features_result.shape}")
            print(f"📊 NaN count: {np.isnan(features_result).sum()}")

    except Exception as e:
        print(f"❌ ОШИБКА В РЕАЛЬНОМ PIPELINE: {e}")
        print("📜 Полная трассировка:")
        traceback.print_exc()

        # Попробуем найти источник ошибки
        if "sqrt" in str(e).lower():
            print("\n🎯 Это ошибка sqrt! Анализируем...")

    print("\n✅ Тест реального pipeline завершен")


async def test_individual_methods():
    """Тестируем отдельные методы FeatureEngineer"""

    print("\n🔬 Тестируем отдельные методы FeatureEngineer...")

    try:
        # Создаем минимальные тестовые данные
        dates = pd.date_range(start="2024-01-01", periods=100, freq="15min")

        df = pd.DataFrame(
            {
                "open": np.random.rand(100) * 50000,
                "high": np.random.rand(100) * 51000,
                "low": np.random.rand(100) * 49000,
                "close": np.random.rand(100) * 50000,
                "volume": np.random.rand(100) * 1000000,
                "symbol": "BTCUSDT",
            },
            index=dates,
        )

        feature_engineer = FeatureEngineer({}, inference_mode=True)

        # Тестируем метод создания волатильности
        print("🧪 Тестируем _create_volatility_features...")
        try:
            result = feature_engineer._create_volatility_features(df.copy())
            print(f"✅ _create_volatility_features прошел: {type(result)}")
        except Exception as e:
            print(f"❌ _create_volatility_features FAILED: {e}")
            traceback.print_exc()

        # Тестируем основной метод
        print("🧪 Тестируем _create_ml_optimized_features...")
        try:
            result = feature_engineer._create_ml_optimized_features(df.copy())
            print(f"✅ _create_ml_optimized_features прошел: {type(result)}")
        except Exception as e:
            print(f"❌ _create_ml_optimized_features FAILED: {e}")
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Общая ошибка в тестах методов: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Запуск debug теста реальной ошибки sqrt...")
    asyncio.run(test_real_sqrt_error())
    asyncio.run(test_individual_methods())
