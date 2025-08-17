#!/usr/bin/env python3
"""
Изолированный тест для поиска ошибки sqrt
"""

import asyncio
import traceback

import numpy as np
import pandas as pd

from core.logger import setup_logger

# Импортируем только необходимые компоненты для воспроизведения
from ml.realtime_indicator_calculator import RealTimeIndicatorCalculator

logger = setup_logger(__name__)


async def test_sqrt_isolation():
    """Изолированное тестирование ошибки sqrt"""

    print("🔍 Изолированный тест ошибки sqrt...")

    try:
        # Создаем корректные тестовые данные как в реальной системе
        dates = pd.date_range(start="2024-01-01", periods=500, freq="15min")

        np.random.seed(42)
        close_prices = 50000 + np.cumsum(np.random.randn(500) * 100)

        ohlcv_df = pd.DataFrame(
            {
                "open": close_prices * (1 + np.random.randn(500) * 0.001),
                "high": close_prices * (1 + np.abs(np.random.randn(500)) * 0.002),
                "low": close_prices * (1 - np.abs(np.random.randn(500)) * 0.002),
                "close": close_prices,
                "volume": np.random.rand(500) * 1000000,
                "turnover": np.random.rand(500) * 50000000,
                "symbol": "BTCUSDT",
            },
            index=dates,
        )

        print(f"✅ Создан OHLCV DataFrame: {ohlcv_df.shape}")

        # Создаем RealTimeIndicatorCalculator как в реальной системе
        config = {"ml": {"cache_ttl": 60}}

        indicator_calculator = RealTimeIndicatorCalculator(
            cache_ttl=60, config=config, use_inference_mode=True
        )

        print("✅ RealTimeIndicatorCalculator создан")

        # Тестируем calculate_indicators
        print("🚀 Тестируем calculate_indicators...")

        indicators = await indicator_calculator.calculate_indicators(
            symbol="BTCUSDT",
            ohlcv_df=ohlcv_df,
            save_to_db=False,  # Отключаем сохранение для теста
        )

        print(f"✅ Индикаторы рассчитаны: {type(indicators)}")

        # Тестируем prepare_ml_input
        print("🚀 Тестируем prepare_ml_input...")

        features_array, metadata = await indicator_calculator.prepare_ml_input(
            symbol="BTCUSDT", ohlcv_df=ohlcv_df, lookback=96
        )

        print(f"✅ ML input подготовлен: {features_array.shape}")
        print(f"📊 Metadata: {metadata}")

        print("🎉 Тест завершен БЕЗ ошибок!")

    except Exception as e:
        print(f"❌ ОШИБКА В ИЗОЛИРОВАННОМ ТЕСТЕ: {e}")
        print("📜 Полная трассировка:")
        traceback.print_exc()

        # Детальный анализ ошибки
        if "sqrt" in str(e).lower():
            print("\n🎯 Это ошибка sqrt! Детальный анализ:")
            error_str = str(e)
            print(f"   - Тип ошибки: {type(e)}")
            print(f"   - Сообщение: {error_str}")

        return False

    return True


if __name__ == "__main__":
    print("🚀 Запуск изолированного теста ошибки sqrt...")
    result = asyncio.run(test_sqrt_isolation())

    if result:
        print("✅ Изолированный тест ПРОШЕЛ - ошибка sqrt исправлена!")
    else:
        print("❌ Изолированный тест ПРОВАЛЕН - ошибка sqrt все еще есть!")
