#!/usr/bin/env python3
"""
Скрипт для отладки ML системы в real-time режиме
Поможет найти где именно теряются признаки
"""

import asyncio
import logging

import numpy as np
import pandas as pd

# Настройка детального логирования
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def debug_step_by_step():
    """Пошаговая отладка ML системы"""

    print("=" * 60)
    print("ОТЛАДКА ML СИСТЕМЫ - ПОШАГОВЫЙ АНАЛИЗ")
    print("=" * 60)

    # Шаг 1: Проверка импорта FeatureEngineer
    print("\n1. Тестирование импорта FeatureEngineer...")
    try:
        from ml.logic.feature_engineering import FeatureEngineer

        # Создаем базовую конфигурацию для FeatureEngineer (пустая конфигурация работает)
        config = {}
        fe = FeatureEngineer(config)
        print(f"✅ FeatureEngineer импортирован: {type(fe)}")

        # Тест на простых данных (добавляем все необходимые колонки)
        close_prices = np.random.uniform(40000, 50000, 100)
        volumes = np.random.uniform(1000, 10000, 100)
        test_df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2023-01-01", periods=100, freq="1min"),
                "open": np.random.uniform(40000, 50000, 100),
                "high": np.random.uniform(50000, 60000, 100),
                "low": np.random.uniform(30000, 40000, 100),
                "close": close_prices,
                "volume": volumes,
                "turnover": close_prices * volumes,  # turnover = close * volume
                "symbol": ["BTCUSDT"] * 100,
                "datetime": pd.date_range("2023-01-01", periods=100, freq="1min"),
            }
        )

        features = await fe.create_features(test_df)
        print(f"✅ Тест на синтетических данных: {features.shape}")

    except Exception as e:
        print(f"❌ Ошибка импорта FeatureEngineer: {e}")
        import traceback

        traceback.print_exc()
        return

    # Шаг 2: Проверка DataLoader
    print("\n2. Тестирование DataLoader...")
    try:
        from data.data_loader import DataLoader

        data_loader = DataLoader()
        await data_loader.initialize()

        df = await data_loader.load_ohlcv("BTCUSDT", "bybit", "15m", limit=100)
        print("✅ DataLoader результат:")
        print(f"   Тип: {type(df)}")
        print(f"   Shape: {df.shape if df is not None else 'None'}")
        print(f"   Columns: {list(df.columns) if df is not None else 'None'}")
        print(f"   Empty: {df.empty if df is not None else 'N/A'}")

        if df is not None and not df.empty:
            print(f"   Sample data: {df.head(2).to_dict()}")

            # Тест FeatureEngineer на реальных данных
            real_features = await fe.create_features(df)
            print(f"✅ FeatureEngineer на реальных данных: {real_features.shape}")
        else:
            print("❌ DataLoader возвращает пустые данные!")

    except Exception as e:
        print(f"❌ Ошибка DataLoader: {e}")
        import traceback

        traceback.print_exc()

    # Шаг 3: Проверка MLSignalProcessor
    print("\n3. Тестирование MLSignalProcessor...")
    try:
        from ml.ml_signal_processor import MLSignalProcessor

        processor = MLSignalProcessor()
        await processor.initialize()
        print("✅ MLSignalProcessor инициализирован")

        # Проверяем что FeatureEngineer создался правильно
        if hasattr(processor, "feature_engineer"):
            fe_type = type(processor.feature_engineer)
            print(f"✅ FeatureEngineer в processor: {fe_type}")
        else:
            print("❌ feature_engineer не найден в processor")

    except Exception as e:
        print(f"❌ Ошибка MLSignalProcessor: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)
    print("ОТЛАДКА ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(debug_step_by_step())
