#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Прямой тест дисперсий в данных без FeatureEngineer
"""

import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).parent))

print("🧪 Тест дисперсий в прямых данных...")

# Создаем тестовые данные
np.random.seed(42)

# Сильно различающиеся данные
btc_prices = 40000 + np.random.randn(100) * 2000
eth_prices = 2500 + np.random.randn(100) * 100

print(f"BTC: mean={np.mean(btc_prices):.2f}, std={np.std(btc_prices):.2f}")
print(f"ETH: mean={np.mean(eth_prices):.2f}, std={np.std(eth_prices):.2f}")

# Простейшая нормализация (как делает FeatureEngineer)
btc_normalized = (btc_prices - np.mean(btc_prices)) / np.std(btc_prices)
eth_normalized = (eth_prices - np.mean(eth_prices)) / np.std(eth_prices)

print(
    f"BTC normalized: mean={np.mean(btc_normalized):.6f}, std={np.std(btc_normalized):.6f}"
)
print(
    f"ETH normalized: mean={np.mean(eth_normalized):.6f}, std={np.std(eth_normalized):.6f}"
)

# Проверяем различия
difference = np.mean(np.abs(btc_normalized - eth_normalized))
print(f"Средняя разность после нормализации: {difference:.6f}")

if difference < 0.1:
    print("❌ ПРОБЛЕМА: После нормализации данные слишком похожи!")
else:
    print("✅ После нормализации данные различны")


# Тестируем робастную нормализацию (как в исправленном коде)
def robust_normalize(data):
    q25, q75 = np.percentile(data, [25, 75])
    iqr = q75 - q25
    if iqr > 1e-8:
        median = np.median(data)
        normalized = (data - median) / iqr
        return np.clip(normalized, -3, 3)
    else:
        return data


btc_robust = robust_normalize(btc_prices)
eth_robust = robust_normalize(eth_prices)

print(f"BTC robust: mean={np.mean(btc_robust):.6f}, std={np.std(btc_robust):.6f}")
print(f"ETH robust: mean={np.mean(eth_robust):.6f}, std={np.std(eth_robust):.6f}")

difference_robust = np.mean(np.abs(btc_robust - eth_robust))
print(f"Средняя разность после робастной нормализации: {difference_robust:.6f}")

if difference_robust < 0.1:
    print("❌ ПРОБЛЕМА: Робастная нормализация тоже дает похожие результаты!")
else:
    print("✅ Робастная нормализация сохраняет различия")
