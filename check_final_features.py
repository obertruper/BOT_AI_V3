#!/usr/bin/env python3
"""
Проверка финальных признаков для ML модели
"""

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from ml.logic.feature_engineering_v2 import FeatureEngineer

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

print(f"Всего числовых колонок: {len(numeric_cols)}")

# Фильтруем target переменные
target_cols = [col for col in numeric_cols if "target" in col.lower()]
feature_cols = [col for col in numeric_cols if "target" not in col.lower()]

print(f"Target колонок: {len(target_cols)}")
print(f"Feature колонок: {len(feature_cols)}")

if len(target_cols) > 0:
    print("\nTarget колонки:")
    for col in target_cols:
        print(f"  - {col}")

print(f"\n✅ Итоговое количество признаков для ML: {len(feature_cols)}")

if len(feature_cols) != 240:
    print(f"⚠️ Предупреждение: ожидается 240 признаков, получено {len(feature_cols)}")

    # Показываем лишние или недостающие
    if len(feature_cols) > 240:
        extra = len(feature_cols) - 240
        print(f"\nНужно удалить {extra} признаков.")
        print("Последние признаки (кандидаты на удаление):")
        for col in feature_cols[-extra - 5 :]:
            print(f"  - {col}")
else:
    print("✅ Количество признаков соответствует модели!")
