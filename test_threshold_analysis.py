#!/usr/bin/env python3
"""
Анализ порогов weighted_direction для калибровки
"""

import numpy as np

# Весы для 4 таймфреймов (15m, 1h, 4h, 12h)
weights = np.array([0.4, 0.3, 0.2, 0.1])

# Возможные комбинации направлений (0=LONG, 1=SHORT, 2=NEUTRAL)
test_cases = [
    # Четкие направления
    ([0, 0, 0, 0], "Все LONG"),
    ([1, 1, 1, 1], "Все SHORT"),
    ([2, 2, 2, 2], "Все NEUTRAL"),
    # Смешанные с преобладанием LONG
    ([0, 0, 0, 1], "Преимущественно LONG"),
    ([0, 0, 1, 1], "LONG/SHORT пополам"),
    ([0, 1, 1, 1], "Преимущественно SHORT"),
    # Смешанные с NEUTRAL
    ([0, 0, 2, 2], "LONG/NEUTRAL"),
    ([1, 1, 2, 2], "SHORT/NEUTRAL"),
    ([0, 1, 2, 2], "Все три типа равномерно"),
    # Текущие наблюдаемые паттерны
    ([2, 1, 2, 1], "Наблюдаемый 1 (NEUTRAL/SHORT)"),
    ([2, 0, 2, 1], "Наблюдаемый 2 (NEUTRAL/LONG/SHORT)"),
]

print("Анализ weighted_direction для разных паттернов:")
print("=" * 60)

for directions, description in test_cases:
    directions = np.array(directions)
    weighted_score = np.sum(directions * weights)

    # Текущие пороги
    if weighted_score < 0.7:
        current_signal = "LONG"
    elif weighted_score < 1.3:
        current_signal = "SHORT"
    else:
        current_signal = "NEUTRAL"

    # Старые пороги для сравнения
    if weighted_score < 0.5:
        old_signal = "LONG"
    elif weighted_score < 1.5:
        old_signal = "SHORT"
    else:
        old_signal = "NEUTRAL"

    print(
        f"{description:30s} | Directions: {directions} | Score: {weighted_score:.3f} | New: {current_signal:7s} | Old: {old_signal:7s}"
    )

# Рекомендуемые пороги на основе анализа
print("\n" + "=" * 60)
print("РЕКОМЕНДАЦИИ ДЛЯ СБАЛАНСИРОВАННОГО РАСПРЕДЕЛЕНИЯ:")
print("=" * 60)

optimal_thresholds = [
    (0.8, 1.2, "Консервативный (узкие диапазоны)"),
    (0.9, 1.1, "Очень консервативный"),
    (0.6, 1.4, "Либеральный (широкие диапазоны)"),
    (0.75, 1.25, "Сбалансированный (рекомендуемый)"),
]

for th1, th2, desc in optimal_thresholds:
    print(f"\n{desc}: LONG < {th1}, SHORT < {th2}, NEUTRAL >= {th2}")

    long_count = short_count = neutral_count = 0

    for directions, _ in test_cases:
        directions = np.array(directions)
        weighted_score = np.sum(directions * weights)

        if weighted_score < th1:
            long_count += 1
        elif weighted_score < th2:
            short_count += 1
        else:
            neutral_count += 1

    total = len(test_cases)
    print(
        f"  Распределение: LONG {long_count}/{total} ({long_count / total * 100:.1f}%), SHORT {short_count}/{total} ({short_count / total * 100:.1f}%), NEUTRAL {neutral_count}/{total} ({neutral_count / total * 100:.1f}%)"
    )
