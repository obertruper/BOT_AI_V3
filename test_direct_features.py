#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Прямой тест метода _handle_nan_values
"""

import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).parent))

from core.config.config_manager import ConfigManager
from ml.logic.feature_engineering import FeatureEngineer

# Создаем экземпляр
config_manager = ConfigManager()
config = config_manager.get_config()
fe = FeatureEngineer(config)

# Тестовые данные с большими различиями
data1 = np.array([[40000, 2000, 100], [41000, 2100, 110], [39000, 1900, 90]])
data2 = np.array([[2500, 100, 50], [2600, 110, 55], [2400, 90, 45]])

print("Исходные данные:")
print(f"Data1 (BTC-like): \n{data1}")
print(f"Data2 (ETH-like): \n{data2}")

# Применяем метод
result1 = fe._handle_nan_values(data1.copy())
result2 = fe._handle_nan_values(data2.copy())

print("\nПосле _handle_nan_values:")
print(f"Result1: \n{result1}")
print(f"Result2: \n{result2}")

# Проверка различий
diff = np.abs(result1 - result2)
print(f"\nРазличия: \n{diff}")
print(f"Средняя разность: {np.mean(diff):.2f}")

if np.mean(diff) < 1.0:
    print("❌ ПРОБЛЕМА: Данные слишком похожи после обработки!")
else:
    print("✅ УСПЕХ: Данные остаются различными!")
