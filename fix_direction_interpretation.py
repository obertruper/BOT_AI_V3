#!/usr/bin/env python3
"""
Исправление интерпретации direction outputs на основе анализа LLM TRANSFORM
"""

import numpy as np


def analyze_model_outputs():
    """Анализ выходов модели и правильная интерпретация."""

    print("🔍 АНАЛИЗ ВЫХОДОВ МОДЕЛИ\n")

    # Текущие выходы модели (из логов)
    raw_outputs = np.array(
        [
            -4.8948632e-06,
            -1.9764666e-04,
            1.2558622e-04,
            1.9886262e-05,  # 0-3: future returns
            2.0000000e00,
            2.0000000e00,
            2.0000000e00,
            1.0000000e00,  # 4-7: directions?
            3.0408299e-01,
            -6.4564019e-01,
            -6.5502888e-01,
            -1.4570761e00,  # 8-11: levels
            1.5410438e00,
            6.8647528e-01,
            1.5426679e00,
            6.1124212e-01,  # 12-15: levels
            -6.1672757e-04,
            2.7367978e-03,
            3.7114308e-03,
            -1.4424557e-03,  # 16-19: risk
        ]
    )

    print("📊 Структура выходов модели (20 значений):")
    print(f"Raw outputs: {raw_outputs}")

    # Анализ direction outputs (позиции 4-7)
    directions_raw = raw_outputs[4:8]
    print(f"\n🎯 Direction outputs (4-7): {directions_raw}")
    print(
        "Проблема: Это не softmax выходы! Значения 2.0 указывают на неправильную интерпретацию"
    )

    # ПРАВИЛЬНАЯ интерпретация (на основе LLM TRANSFORM)
    print("\n✅ ПРАВИЛЬНАЯ ИНТЕРПРЕТАЦИЯ:")

    # В LLM TRANSFORM direction_head выдает 12 значений (позиции 4-15)
    # Структура: 3 класса × 4 таймфрейма = 12 значений

    if len(raw_outputs) >= 16:
        # Возможная правильная структура:
        # 4-15: direction predictions (12 values)
        # Каждые 3 значения - это softmax для одного таймфрейма

        print("\n📈 Если direction_head выдает 12 значений (4-15):")
        direction_values = raw_outputs[4:16]
        print(f"Direction values: {direction_values}")

        # Разбиваем на 4 таймфрейма по 3 класса
        for i in range(4):
            start_idx = i * 3
            end_idx = start_idx + 3
            timeframe_predictions = direction_values[start_idx:end_idx]

            print(f"\nТаймфрейм {i + 1}:")
            print(f"  Raw: {timeframe_predictions}")

            # Применяем softmax
            exp_vals = np.exp(timeframe_predictions - np.max(timeframe_predictions))
            softmax_probs = exp_vals / exp_vals.sum()
            print(f"  Softmax: {softmax_probs}")

            # Определяем класс
            predicted_class = np.argmax(softmax_probs)
            class_names = ["SHORT", "NEUTRAL", "LONG"]
            print(
                f"  Предсказание: {class_names[predicted_class]} (confidence: {softmax_probs[predicted_class]:.1%})"
            )

    # Альтернативная интерпретация (если выходы уже обработаны)
    print("\n📊 Альтернативная интерпретация (если значения уже обработаны):")
    print("Значения [2.0, 2.0, 2.0, 1.0] могут означать:")
    print("- 2.0 = LONG (класс 2)")
    print("- 1.0 = NEUTRAL (класс 1)")
    print("- 0.0 = SHORT (класс 0)")

    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ ДЛЯ ИСПРАВЛЕНИЯ:")
    print("1. Проверить архитектуру модели - сколько выходов у direction_head")
    print("2. Если 12 выходов - использовать softmax и argmax для каждого таймфрейма")
    print("3. Если 4 выхода - это уже классы, не нужна дополнительная обработка")
    print("4. Исправить интерпретацию в ml_manager._interpret_predictions()")

    # Пример правильной функции
    print("\n📝 Пример правильной функции интерпретации:")
    print(
        """
def _interpret_predictions(self, outputs):
    outputs_np = outputs.cpu().numpy()[0]

    # Вариант 1: direction_head выдает 12 значений (3 класса × 4 таймфрейма)
    if outputs_np.shape[0] >= 16:
        direction_logits = outputs_np[4:16].reshape(4, 3)  # 4 таймфрейма × 3 класса

        directions = []
        for logits in direction_logits:
            probs = torch.softmax(torch.tensor(logits), dim=0)
            direction = torch.argmax(probs).item()
            directions.append(direction)

        # Взвешенное среднее для основного сигнала
        weights = [0.4, 0.3, 0.2, 0.1]  # Больший вес ближним таймфреймам
        weighted_direction = sum(d * w for d, w in zip(directions, weights))

        if weighted_direction < 0.5:
            signal_type = "SHORT"
        elif weighted_direction > 1.5:
            signal_type = "LONG"
        else:
            signal_type = "NEUTRAL"

    # Вариант 2: direction_head выдает 4 значения (уже классы)
    else:
        directions = outputs_np[4:8]
        # Интерпретация: 0=SHORT, 1=NEUTRAL, 2=LONG
        signal_map = {0: "SHORT", 1: "NEUTRAL", 2: "LONG"}

        # Подсчет голосов
        signal_counts = {}
        for d in directions:
            signal = signal_map.get(int(d), "NEUTRAL")
            signal_counts[signal] = signal_counts.get(signal, 0) + 1

        # Выбор наиболее частого сигнала
        signal_type = max(signal_counts, key=signal_counts.get)
    """
    )


if __name__ == "__main__":
    analyze_model_outputs()
