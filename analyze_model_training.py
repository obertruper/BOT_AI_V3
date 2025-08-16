#!/usr/bin/env python3
"""
Анализ обучения модели из checkpoint
"""

from pathlib import Path

import torch


def analyze_training():
    """Анализ истории обучения модели"""

    print("=" * 70)
    print("📊 АНАЛИЗ ОБУЧЕНИЯ МОДЕЛИ")
    print("=" * 70)

    # Загружаем checkpoint
    model_path = Path("models/saved/best_model_20250728_215703.pth")
    checkpoint = torch.load(model_path, map_location="cpu")

    # 1. Анализ истории обучения
    if "history" in checkpoint:
        history = checkpoint["history"]
        print("\n📈 ИСТОРИЯ ОБУЧЕНИЯ:")
        print("-" * 50)

        if "train_loss" in history:
            train_losses = history["train_loss"]
            print(f"Эпох обучения: {len(train_losses)}")
            print(f"Начальный train loss: {train_losses[0]:.4f}")
            print(f"Финальный train loss: {train_losses[-1]:.4f}")
            print(f"Лучший train loss: {min(train_losses):.4f}")

        if "val_loss" in history:
            val_losses = history["val_loss"]
            print(f"\nНачальный val loss: {val_losses[0]:.4f}")
            print(f"Финальный val loss: {val_losses[-1]:.4f}")
            print(f"Лучший val loss: {min(val_losses):.4f}")

            # Проверка на переобучение
            if len(train_losses) > 0 and len(val_losses) > 0:
                final_gap = val_losses[-1] - train_losses[-1]
                print(f"\nРазница train/val на конец: {final_gap:.4f}")
                if final_gap > 0.5:
                    print("⚠️ Возможное переобучение!")

        # Метрики точности
        if "val_direction_acc" in history:
            val_acc = history["val_direction_acc"]
            print("\n🎯 ТОЧНОСТЬ ПРЕДСКАЗАНИЯ НАПРАВЛЕНИЯ:")
            print(f"Начальная точность: {val_acc[0]:.1%}")
            print(f"Финальная точность: {val_acc[-1]:.1%}")
            print(f"Лучшая точность: {max(val_acc):.1%}")

    # 2. Финальные метрики
    print("\n📊 ФИНАЛЬНЫЕ МЕТРИКИ МОДЕЛИ:")
    print("-" * 50)

    if "best_metrics" in checkpoint:
        metrics = checkpoint["best_metrics"]
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                if "loss" in key:
                    print(f"{key}: {value:.4f}")
                elif "acc" in key or "accuracy" in key:
                    print(f"{key}: {value:.1%}")
                else:
                    print(f"{key}: {value:.4f}")
            elif isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    if isinstance(v, (int, float)):
                        print(f"  {k}: {v:.3f}")

    # 3. Конфигурация обучения
    if "config" in checkpoint:
        config = checkpoint["config"]
        print("\n⚙️ КОНФИГУРАЦИЯ ОБУЧЕНИЯ:")
        print("-" * 50)

        if "training" in config:
            train_cfg = config["training"]
            print(f"Batch size: {train_cfg.get('batch_size', 'N/A')}")
            print(f"Learning rate: {train_cfg.get('lr', 'N/A')}")
            print(f"Epochs: {train_cfg.get('epochs', 'N/A')}")

        if "data" in config:
            data_cfg = config["data"]
            print("\nДанные:")
            print(f"  Symbols: {data_cfg.get('symbols', 'N/A')}")
            print(f"  Sequence length: {data_cfg.get('sequence_length', 'N/A')}")
            print(f"  Features: {data_cfg.get('num_features', 'N/A')}")

    # 4. Проверка весов модели
    print("\n🔍 АНАЛИЗ ВЕСОВ МОДЕЛИ:")
    print("-" * 50)

    state_dict = checkpoint["model_state_dict"]

    # Анализ direction head
    direction_weights = []
    for key in state_dict.keys():
        if "direction" in key.lower() and "weight" in key:
            weights = state_dict[key]
            direction_weights.append(weights)

            # Статистика весов
            w_mean = weights.mean().item()
            w_std = weights.std().item()
            w_min = weights.min().item()
            w_max = weights.max().item()

            print(f"\n{key}:")
            print(f"  Shape: {list(weights.shape)}")
            print(f"  Mean: {w_mean:.6f}")
            print(f"  Std: {w_std:.6f}")
            print(f"  Range: [{w_min:.6f}, {w_max:.6f}]")

            # Проверка на вырожденность
            if w_std < 0.01:
                print("  ⚠️ Очень маленькая дисперсия весов!")
            if abs(w_mean) > 1.0:
                print("  ⚠️ Большое смещение весов!")

    # 5. Проверка выходного слоя
    print("\n🎯 АНАЛИЗ ВЫХОДНОГО СЛОЯ (direction):")
    print("-" * 50)

    # Ищем финальный слой для direction
    final_direction_key = None
    for key in state_dict.keys():
        if "direction" in key.lower() and ("3.weight" in key or "final" in key or "output" in key):
            final_direction_key = key
            break

    if final_direction_key:
        final_weights = state_dict[final_direction_key]
        print(f"Финальный слой: {final_direction_key}")
        print(f"Shape: {list(final_weights.shape)}")

        # Для direction head должно быть [12, 128] -> 12 выходов = 4 таймфрейма × 3 класса
        if final_weights.shape[0] == 12:
            print("✅ Правильная размерность: 12 выходов (4 таймфрейма × 3 класса)")

            # Анализ по классам
            weights_reshaped = final_weights.reshape(4, 3, -1)  # 4 таймфрейма, 3 класса

            for tf in range(4):
                print(f"\nТаймфрейм {tf + 1}:")
                for cls in range(3):
                    class_weights = weights_reshaped[tf, cls]
                    cls_name = ["LONG", "SHORT", "NEUTRAL"][cls]
                    print(
                        f"  {cls_name}: mean={class_weights.mean():.4f}, std={class_weights.std():.4f}"
                    )

        # Проверка bias
        bias_key = final_direction_key.replace("weight", "bias")
        if bias_key in state_dict:
            bias = state_dict[bias_key]
            print(f"\nBias: {bias.numpy()}")

            if bias.shape[0] == 12:
                bias_reshaped = bias.reshape(4, 3)
                print("\nBias по классам:")
                for tf in range(4):
                    print(
                        f"  TF{tf + 1}: LONG={bias_reshaped[tf, 0]:.4f}, SHORT={bias_reshaped[tf, 1]:.4f}, NEUTRAL={bias_reshaped[tf, 2]:.4f}"
                    )

    print("\n" + "=" * 70)
    print("💡 ВЫВОДЫ И РЕКОМЕНДАЦИИ:")
    print("=" * 70)

    # Проверяем признаки проблем
    problems = []

    # Проверка истории
    if "history" in checkpoint:
        if "val_direction_acc" in checkpoint["history"]:
            final_acc = checkpoint["history"]["val_direction_acc"][-1]
            if final_acc < 0.4:
                problems.append(f"Низкая точность модели: {final_acc:.1%}")
            elif final_acc > 0.35 and final_acc < 0.36:
                problems.append("Точность ~33% указывает на случайные предсказания (3 класса)")

    # Проверка val_loss
    if "val_loss" in checkpoint:
        val_loss = checkpoint["val_loss"]
        if val_loss > 2.0:
            problems.append(f"Высокий val_loss: {val_loss:.4f}")

    if problems:
        print("\n❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("\n✅ Модель обучена корректно")

    print(
        """
📝 РЕКОМЕНДАЦИИ ДЛЯ ПРАВИЛЬНОЙ ИНТЕГРАЦИИ:

1. Проверить соответствие признаков:
   - В обучении использовалось 240 признаков
   - Убедиться что feature_engineering генерирует те же признаки

2. Проверить нормализацию:
   - Использовать тот же scaler что и при обучении
   - Файл: models/saved/data_scaler.pkl

3. Проверить предобработку данных:
   - Правильная сортировка по времени
   - Правильный context_length (96 свечей)

4. Если модель была качественной при обучении но плохо работает сейчас:
   - Данные изменились (другой рынок)
   - Неправильная предобработка
   - Несоответствие версий библиотек
    """
    )


if __name__ == "__main__":
    analyze_training()
