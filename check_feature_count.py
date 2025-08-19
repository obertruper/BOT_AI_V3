#!/usr/bin/env python3
"""
Проверка количества генерируемых признаков
"""

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from ml.logic.archive_old_versions.feature_engineering_v2 import FeatureEngineer

# Создаем тестовые данные
periods = 500
dates = pd.date_range(end=datetime.now(UTC), periods=periods, freq="15min")

# Симулируем ценовые данные
prices = np.linspace(100000, 102000, periods) + np.random.normal(0, 200, periods)

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

# Создаем признаки
fe = FeatureEngineer({})
features_df = fe.create_features(df.copy())

# Извлекаем числовые колонки
numeric_cols = features_df.select_dtypes(include=[np.number]).columns.tolist()

print(f"Всего колонок: {len(features_df.columns)}")
print(f"Числовых колонок: {len(numeric_cols)}")
print()

# Группируем по типам
basic_features = [
    col for col in numeric_cols if any(x in col for x in ["returns", "ratio", "position", "vwap"])
]
tech_indicators = [
    col
    for col in numeric_cols
    if any(
        x in col
        for x in [
            "sma",
            "ema",
            "rsi",
            "macd",
            "bb_",
            "atr",
            "stoch",
            "adx",
            "mfi",
            "cci",
            "williams",
            "obv",
        ]
    )
]
ml_features = [
    col
    for col in numeric_cols
    if any(x in col for x in ["hurst", "fractal", "efficiency", "entropy", "clustering", "noise"])
]
microstructure = [
    col
    for col in numeric_cols
    if any(x in col for x in ["spread", "imbalance", "pressure", "flow", "amihud", "kyle", "vpin"])
]
advanced_tech = [
    col for col in numeric_cols if any(x in col for x in ["ichimoku", "keltner", "donchian"])
]

print(f"Базовые признаки: {len(basic_features)}")
print(f"Технические индикаторы: {len(tech_indicators)}")
print(f"ML-оптимизированные: {len(ml_features)}")
print(f"Микроструктура: {len(microstructure)}")
print(f"Расширенные технические: {len(advanced_tech)}")

# Нужно обеспечить ровно 240 признаков
target_features = 240
current_features = len(numeric_cols)

print()
print(f"Текущее количество признаков: {current_features}")
print(f"Требуется для модели: {target_features}")

if current_features > target_features:
    print(f"⚠️ Слишком много признаков! Нужно удалить {current_features - target_features}")

    # Выводим последние признаки, которые можно удалить
    print("\nПоследние признаки (можно удалить):")
    for col in numeric_cols[-30:]:
        print(f"  - {col}")
elif current_features < target_features:
    print(f"⚠️ Недостаточно признаков! Нужно добавить {target_features - current_features}")
else:
    print("✅ Количество признаков соответствует модели!")
