#!/usr/bin/env python3
"""
Проверка архитектуры модели из checkpoint
"""

from pathlib import Path

import torch


def check_model_architecture():
    """Проверяет архитектуру модели из сохраненного checkpoint."""

    print("🔍 ПРОВЕРКА АРХИТЕКТУРЫ МОДЕЛИ\n")

    # Путь к модели
    model_path = Path(
        "/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3/models/saved/best_model_20250728_215703.pth"
    )

    # Загружаем checkpoint
    checkpoint = torch.load(model_path, map_location="cpu")
    state_dict = checkpoint["model_state_dict"]

    print("📊 Анализ direction_head в модели:")
    print("-" * 60)

    # Ищем все слои связанные с direction
    direction_layers = {}
    for name, tensor in state_dict.items():
        if "direction" in name.lower():
            direction_layers[name] = tensor
            print(f"{name}: shape={tensor.shape}")

    print("\n📊 Анализ всех head слоев:")
    print("-" * 60)

    # Группируем по типам head
    heads = {}
    for name, tensor in state_dict.items():
        if "_head" in name:
            head_type = name.split(".")[0]
            if head_type not in heads:
                heads[head_type] = []
            heads[head_type].append((name, tensor.shape))

    for head_type, layers in sorted(heads.items()):
        print(f"\n{head_type}:")
        for layer_name, shape in layers:
            print(f"  {layer_name}: {shape}")

    # Специальный анализ direction_head
    print("\n🎯 ДЕТАЛЬНЫЙ АНАЛИЗ direction_head:")
    print("-" * 60)

    # Проверяем последний Linear слой
    direction_final_weight = None
    direction_final_bias = None

    for name, tensor in state_dict.items():
        if "direction_head" in name and "weight" in name:
            # Ищем последний слой (наибольший номер)
            if "3.weight" in name:  # Обычно последний слой
                direction_final_weight = tensor
        if "direction_head" in name and "bias" in name:
            if "3.bias" in name:
                direction_final_bias = tensor

    if direction_final_weight is not None:
        print("Финальный слой direction_head:")
        print(f"  Weight shape: {direction_final_weight.shape}")
        print(f"  Output size: {direction_final_weight.shape[0]}")

        if direction_final_weight.shape[0] == 12:
            print("  ✅ Модель выдает 12 значений (3 класса × 4 таймфрейма)")
            print("  Структура: каждые 3 значения = softmax для одного таймфрейма")
        elif direction_final_weight.shape[0] == 4:
            print("  ✅ Модель выдает 4 значения (по одному классу на таймфрейм)")
        elif direction_final_weight.shape[0] == 3:
            print("  ✅ Модель выдает 3 значения (3 класса для одного таймфрейма)")

    if direction_final_bias is not None:
        print(f"\n  Bias shape: {direction_final_bias.shape}")
        print(f"  Bias values: {direction_final_bias.cpu().numpy()}")

    # Проверяем общую структуру выходов
    print("\n📊 СТРУКТУРА ВСЕХ ВЫХОДОВ МОДЕЛИ:")
    print("-" * 60)

    total_outputs = 0
    output_structure = []

    # Порядок head'ов важен!
    head_order = [
        "future_returns_head",
        "direction_head",
        "long_levels_head",
        "short_levels_head",
        "risk_metrics_head",
        "confidence_head",
    ]

    for head_name in head_order:
        for name, tensor in state_dict.items():
            if head_name in name and "3.bias" in name:  # Последний слой
                size = tensor.shape[0]
                output_structure.append(
                    (head_name, size, total_outputs, total_outputs + size)
                )
                total_outputs += size

    print(f"Общее количество выходов: {total_outputs}")
    print("\nСтруктура выходов:")
    for head_name, size, start, end in output_structure:
        print(f"  [{start:2d}-{end - 1:2d}]: {head_name:<25} ({size} outputs)")

    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ ДЛЯ ИСПРАВЛЕНИЯ:")
    print("-" * 60)

    if any(
        "direction_head" in name and tensor.shape[0] == 12
        for name, tensor in state_dict.items()
        if "3.bias" in name
    ):
        print("1. direction_head выдает 12 значений")
        print("2. Нужно изменить интерпретацию в _interpret_predictions():")
        print("   - Взять outputs[4:16] для directions")
        print("   - Разбить на 4 группы по 3 значения")
        print("   - Применить softmax и argmax к каждой группе")
        print("3. Сдвинуть индексы для остальных outputs:")
        print("   - level_targets начинаются с 16, а не с 8")
        print("   - risk_metrics начинаются с 24, а не с 16")


if __name__ == "__main__":
    check_model_architecture()
