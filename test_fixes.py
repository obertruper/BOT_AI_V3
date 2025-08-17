#!/usr/bin/env python3
"""
Тест исправлений для ошибки sqrt и отсутствующих признаков
"""

import asyncio
import traceback

import numpy as np
import pandas as pd

from core.logger import setup_logger
from ml.config.features_240 import get_required_features_list

# Импортируем реальные компоненты
from ml.logic.feature_engineering_v2 import FeatureEngineer

logger = setup_logger(__name__)


async def test_fixes():
    """Тестируем исправления"""

    print("🔍 Тестируем исправления для ошибок sqrt и отсутствующих признаков...")

    try:
        # Создаем корректные тестовые данные с datetime в индексе
        dates = pd.date_range(start="2024-01-01", periods=300, freq="15min")

        np.random.seed(42)
        close_prices = 50000 + np.cumsum(np.random.randn(300) * 100)

        df = pd.DataFrame(
            {
                "open": close_prices * (1 + np.random.randn(300) * 0.001),
                "high": close_prices * (1 + np.abs(np.random.randn(300)) * 0.002),
                "low": close_prices * (1 - np.abs(np.random.randn(300)) * 0.002),
                "close": close_prices,
                "volume": np.random.rand(300) * 1000000,
                "turnover": np.random.rand(300) * 50000000,
                "symbol": "BTCUSDT",
            },
            index=dates,
        )

        print(f"✅ Создан тестовый DataFrame: {df.shape}")
        print(f"📅 Index type: {type(df.index)}")
        print(f"📋 Columns: {list(df.columns)}")

        # Создаем FeatureEngineer
        config = {"inference_mode": True, "disable_progress": False}

        feature_engineer = FeatureEngineer(config, inference_mode=True)
        print("✅ FeatureEngineer создан")

        # Тестируем создание признаков
        print("🚀 Запускаем create_features...")

        features_result = feature_engineer.create_features(df)

        print(f"✅ Признаки сгенерированы: {type(features_result)}")

        if isinstance(features_result, pd.DataFrame):
            print(f"📊 Shape: {features_result.shape}")
            print(f"📊 Columns: {len(features_result.columns)}")
            print(f"📊 NaN count: {features_result.isna().sum().sum()}")

            # Проверяем отсутствующие признаки
            required_features = get_required_features_list()
            present_features = list(features_result.columns)

            missing_features = [f for f in required_features if f not in present_features]

            print(f"📋 Требуется признаков: {len(required_features)}")
            print(f"📋 Присутствует признаков: {len(present_features)}")
            print(f"❌ Отсутствует признаков: {len(missing_features)}")

            if missing_features:
                print(f"🔍 Первые 10 отсутствующих: {missing_features[:10]}")
            else:
                print("🎉 Все требуемые признаки присутствуют!")

            # Проверяем volatility_2, volatility_3
            vol_features = [f for f in present_features if "volatility_" in f]
            print(f"🌊 Volatility признаки: {len(vol_features)}")

            if "volatility_2" in present_features and "volatility_3" in present_features:
                print("✅ volatility_2 и volatility_3 присутствуют!")
            else:
                print("❌ volatility_2 или volatility_3 отсутствуют")

        elif isinstance(features_result, np.ndarray):
            print(f"📊 Array shape: {features_result.shape}")
            print(f"📊 NaN count: {np.isnan(features_result).sum()}")

    except Exception as e:
        print(f"❌ ОШИБКА В ТЕСТЕ: {e}")
        print("📜 Полная трассировка:")
        traceback.print_exc()

        # Анализируем ошибку
        if "sqrt" in str(e).lower():
            print("\n🎯 Это ошибка sqrt! Требуется дальнейший анализ...")
        elif "datetime" in str(e).lower():
            print("\n📅 Это ошибка datetime! Проверьте формат данных...")

    print("\n✅ Тест исправлений завершен")


if __name__ == "__main__":
    print("🚀 Запуск теста исправлений...")
    asyncio.run(test_fixes())
