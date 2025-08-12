#!/usr/bin/env python3
"""Тест расчета confidence"""

import numpy as np

# Симулируем значения из модели
# risk_metrics (outputs 16-19) - обычно близки к 0
risk_metrics = np.array([0.01, 0.02, -0.01, 0.015])

# signal_strength - согласованность направлений (0.25 - 1.0)
# Если 3 из 4 таймфреймов согласны: 3/4 = 0.75
signal_strength = 0.75

# avg_risk - среднее risk_metrics
avg_risk = float(np.mean(risk_metrics))

print("=" * 60)
print("АНАЛИЗ ФОРМУЛЫ CONFIDENCE")
print("=" * 60)

print("\n📊 Входные данные:")
print(f"  risk_metrics: {risk_metrics}")
print(f"  signal_strength: {signal_strength}")
print(f"  avg_risk: {avg_risk:.4f}")

# Из ml_manager.py строки 505-507, 633-635
# confidence_scores = risk_metrics
# model_confidence = np.mean(1.0 / (1.0 + np.exp(-confidence_scores)))
confidence_scores = risk_metrics
model_confidence = float(np.mean(1.0 / (1.0 + np.exp(-confidence_scores))))

print("\n🔍 Промежуточные расчеты:")
print(f"  confidence_scores: {confidence_scores}")
print(f"  sigmoid каждого: {1.0 / (1.0 + np.exp(-confidence_scores))}")
print(f"  model_confidence (среднее sigmoid): {model_confidence:.6f}")

# Из ml_manager.py строки 638-640
# combined_confidence = signal_strength * 0.4 + model_confidence * 0.4 + (1.0 - avg_risk) * 0.2
combined_confidence = (
    signal_strength * 0.4 + model_confidence * 0.4 + (1.0 - avg_risk) * 0.2
)

print("\n📈 Итоговый расчет:")
print(
    "  combined_confidence = signal_strength * 0.4 + model_confidence * 0.4 + (1.0 - avg_risk) * 0.2"
)
print(
    f"  combined_confidence = {signal_strength:.2f} * 0.4 + {model_confidence:.4f} * 0.4 + {1.0 - avg_risk:.4f} * 0.2"
)
print(
    f"  combined_confidence = {signal_strength * 0.4:.4f} + {model_confidence * 0.4:.4f} + {(1.0 - avg_risk) * 0.2:.4f}"
)
print(f"  combined_confidence = {combined_confidence:.6f}")

print("\n" + "=" * 60)
print("ПРОБЛЕМА НАЙДЕНА!")
print("=" * 60)

print("\nЕсли risk_metrics близки к 0 (что обычно и происходит),")
print("то sigmoid(0) = 0.5, и формула дает:")

# Тест с нулевыми risk_metrics
risk_metrics_zero = np.array([0.0, 0.0, 0.0, 0.0])
model_conf_zero = float(np.mean(1.0 / (1.0 + np.exp(-risk_metrics_zero))))
avg_risk_zero = 0.0

# Разные signal_strength
for ss in [0.25, 0.50, 0.75, 1.0]:
    conf = ss * 0.4 + model_conf_zero * 0.4 + (1.0 - avg_risk_zero) * 0.2
    print(f"  signal_strength={ss:.2f} → confidence={conf:.4f}")

print("\n💡 РЕШЕНИЕ:")
print("1. risk_metrics не должны использоваться как confidence_scores")
print("2. Нужно использовать реальные confidence выходы модели")
print("3. Или правильно интерпретировать выходы модели")

print("\n🎯 Формула при risk_metrics ≈ 0:")
print("  confidence ≈ signal_strength * 0.4 + 0.5 * 0.4 + 1.0 * 0.2")
print("  confidence ≈ signal_strength * 0.4 + 0.2 + 0.2")
print("  confidence ≈ signal_strength * 0.4 + 0.4")
print("\nПри signal_strength = 0.5: confidence = 0.5 * 0.4 + 0.4 = 0.6")
print("При signal_strength = 0.75: confidence = 0.75 * 0.4 + 0.4 = 0.7")
print("\nВСЕ ЗНАЧЕНИЯ БУДУТ В ДИАПАЗОНЕ 0.5 - 0.8!")
