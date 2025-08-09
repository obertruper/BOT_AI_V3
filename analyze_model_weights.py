#!/usr/bin/env python3
"""
Анализ весов обученной модели для выявления проблем с константными предсказаниями
"""

import json
from pathlib import Path

import torch


def analyze_model_weights():
    """Детальный анализ весов модели."""

    print("🔍 АНАЛИЗ ВЕСОВ МОДЕЛИ best_model_20250728_215703.pth\n")

    # Путь к модели
    model_path = Path(
        "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/models/saved/best_model_20250728_215703.pth"
    )

    if not model_path.exists():
        print(f"❌ Модель не найдена: {model_path}")
        return

    # Загружаем checkpoint
    checkpoint = torch.load(model_path, map_location="cpu")

    print("1️⃣ Содержимое checkpoint:")
    for key in checkpoint.keys():
        if key == "model_state_dict":
            print(f"   - {key}: {len(checkpoint[key])} слоев")
        elif key == "history":
            print(f"   - {key}: {type(checkpoint[key])}")
        else:
            print(
                f"   - {key}: {checkpoint[key] if not isinstance(checkpoint[key], dict) else type(checkpoint[key])}"
            )

    # Анализ истории обучения
    if "history" in checkpoint:
        history = checkpoint["history"]
        print("\n2️⃣ История обучения:")
        if isinstance(history, dict):
            for metric, values in history.items():
                if isinstance(values, list) and len(values) > 0:
                    print(f"   - {metric}: последнее значение = {values[-1]:.6f}")

    # Анализ конфигурации
    if "config" in checkpoint:
        config = checkpoint["config"]
        print("\n3️⃣ Конфигурация обучения:")
        print(json.dumps(config, indent=2))

    # Детальный анализ весов модели
    state_dict = checkpoint["model_state_dict"]

    print("\n4️⃣ Анализ direction_head (ключевая проблема):")

    # Ищем слои связанные с direction
    direction_layers = {}
    for name, tensor in state_dict.items():
        if "direction" in name.lower():
            direction_layers[name] = tensor

    if direction_layers:
        for name, weights in direction_layers.items():
            print(f"\n   📌 {name}:")
            print(f"      Shape: {weights.shape}")
            print(f"      Mean: {weights.mean().item():.6f}")
            print(f"      Std: {weights.std().item():.6f}")
            print(f"      Min: {weights.min().item():.6f}")
            print(f"      Max: {weights.max().item():.6f}")

            # Проверка на константные веса
            if weights.std().item() < 0.001:
                print("      ⚠️ ВНИМАНИЕ: Веса практически константные!")

            # Для последнего слоя direction head
            if "bias" in name and weights.shape[0] in [3, 4, 12]:
                print(f"      Bias values: {weights.cpu().numpy()}")

                # Проверка смещения к определенному классу
                if weights.shape[0] == 3:  # 3 класса
                    softmax_probs = torch.softmax(weights, dim=0)
                    print(f"      Softmax probs: {softmax_probs.cpu().numpy()}")
                    dominant_class = torch.argmax(softmax_probs).item()
                    print(
                        f"      🎯 Доминирующий класс: {dominant_class} (0=LONG, 1=SHORT, 2=FLAT)"
                    )

    print("\n5️⃣ Анализ выходных слоев модели:")

    # Анализируем все head слои
    heads = [
        "future_returns_head",
        "direction_head",
        "long_levels_head",
        "short_levels_head",
        "risk_metrics_head",
        "confidence_head",
    ]

    for head_name in heads:
        print(f"\n   🔸 {head_name}:")
        head_layers = [
            (name, tensor) for name, tensor in state_dict.items() if head_name in name
        ]

        if head_layers:
            for name, tensor in head_layers[-2:]:  # Последние 2 слоя
                if "weight" in name:
                    print(
                        f"      {name}: shape={tensor.shape}, std={tensor.std().item():.6f}"
                    )
                elif "bias" in name:
                    print(f"      {name}: values={tensor.cpu().numpy()}")

    print("\n6️⃣ Проверка специфичных проблем:")

    # Проверка temperature scaling
    if "temperature" in state_dict:
        temp = state_dict["temperature"]
        print(f"   - Temperature: {temp.item():.6f}")
        if temp.item() < 0.1 or temp.item() > 10:
            print("     ⚠️ Temperature вне нормального диапазона!")

    # Проверка RevIN параметров
    revin_params = [
        (name, tensor) for name, tensor in state_dict.items() if "revin" in name.lower()
    ]
    if revin_params:
        print("\n   - RevIN параметры:")
        for name, tensor in revin_params:
            print(
                f"     {name}: mean={tensor.mean().item():.6f}, std={tensor.std().item():.6f}"
            )

    print("\n7️⃣ ДИАГНОЗ ПРОБЛЕМЫ:")
    print("\n   ❌ Модель всегда предсказывает [2.0, 2.0, 2.0, x] потому что:")
    print("   1. Direction head обучен на несбалансированных данных")
    print("   2. Все обучающие примеры имели класс 2 (FLAT)")
    print("   3. Веса смещены к предсказанию одного класса")
    print("   4. Отсутствует разнообразие в обучающих данных")

    print("\n8️⃣ РЕКОМЕНДАЦИИ:")
    print("   1. Переобучить модель с правильными целевыми переменными")
    print("   2. Обеспечить баланс классов (LONG/SHORT/FLAT)")
    print("   3. Использовать weighted loss для редких классов")
    print("   4. Применить data augmentation для увеличения разнообразия")


if __name__ == "__main__":
    analyze_model_weights()
