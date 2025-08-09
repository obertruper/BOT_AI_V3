#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простейший тест изменений
"""

import numpy as np


# Имитируем метод _handle_nan_values ДО исправления
def old_handle_nan_values(features_array):
    """Старая версия с робастной нормализацией"""
    features_array = np.nan_to_num(features_array, nan=0.0, posinf=0.0, neginf=0.0)

    for i in range(features_array.shape[1]):
        feature_col = features_array[:, i]
        q25, q75 = np.percentile(feature_col, [25, 75])
        iqr = q75 - q25

        if iqr > 1e-8:
            median = np.median(feature_col)
            features_array[:, i] = (feature_col - median) / iqr
            features_array[:, i] = np.clip(features_array[:, i], -3, 3)
        else:
            features_array[:, i] = feature_col

    return features_array


# Новая версия БЕЗ нормализации
def new_handle_nan_values(features_array):
    """Новая версия - только клиппинг с большими пределами"""
    features_array = np.nan_to_num(features_array, nan=0.0, posinf=1e6, neginf=-1e6)
    features_array = np.clip(features_array, -1e6, 1e6)
    return features_array


# Тестовые данные
btc_data = np.array(
    [[40000, 41000, 39000], [40100, 41100, 39100], [39900, 40900, 38900]]
)
eth_data = np.array([[2500, 2600, 2400], [2510, 2610, 2410], [2490, 2590, 2390]])

print("=== СТАРАЯ ВЕРСИЯ (с нормализацией) ===")
btc_old = old_handle_nan_values(btc_data.copy())
eth_old = old_handle_nan_values(eth_data.copy())
print(f"BTC после старой обработки:\n{btc_old}")
print(f"ETH после старой обработки:\n{eth_old}")
print(f"Средняя разность: {np.mean(np.abs(btc_old - eth_old)):.6f}")

print("\n=== НОВАЯ ВЕРСИЯ (без нормализации) ===")
btc_new = new_handle_nan_values(btc_data.copy())
eth_new = new_handle_nan_values(eth_data.copy())
print(f"BTC после новой обработки:\n{btc_new}")
print(f"ETH после новой обработки:\n{eth_new}")
print(f"Средняя разность: {np.mean(np.abs(btc_new - eth_new)):.2f}")

print("\n📊 РЕЗУЛЬТАТ:")
if np.mean(np.abs(btc_old - eth_old)) < 1.0:
    print("❌ Старая версия делает данные похожими")
else:
    print("✅ Старая версия сохраняет различия")

if np.mean(np.abs(btc_new - eth_new)) < 1.0:
    print("❌ Новая версия делает данные похожими")
else:
    print("✅ Новая версия сохраняет различия")
