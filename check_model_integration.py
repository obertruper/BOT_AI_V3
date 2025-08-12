#!/usr/bin/env python3
"""
Проверка правильности интеграции модели из проекта обучения
"""

import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent))


def check_model():
    """Проверка модели и её параметров"""

    print("=" * 60)
    print("🔍 ПРОВЕРКА ИНТЕГРАЦИИ МОДЕЛИ")
    print("=" * 60)

    # 1. Загружаем checkpoint
    model_path = Path("models/saved/best_model_20250728_215703.pth")
    if not model_path.exists():
        print(f"❌ Модель не найдена: {model_path}")
        return

    print(f"\n📦 Загружаем модель: {model_path}")
    checkpoint = torch.load(model_path, map_location="cpu")

    # 2. Проверяем содержимое checkpoint
    print("\n📋 Содержимое checkpoint:")
    for key in checkpoint.keys():
        if key == "model_state_dict":
            print(f"  - {key}: {len(checkpoint[key])} параметров")
        else:
            print(
                f"  - {key}: {checkpoint[key] if not isinstance(checkpoint[key], dict) else f'{len(checkpoint[key])} элементов'}"
            )

    # 3. Проверяем архитектуру модели
    if "config" in checkpoint:
        config = checkpoint["config"]
        print("\n🏗️ Конфигурация модели из checkpoint:")
        if "model" in config:
            model_config = config["model"]
            print(f"  - input_size: {model_config.get('input_size', 'не указан')}")
            print(f"  - output_size: {model_config.get('output_size', 'не указан')}")
            print(
                f"  - context_window: {model_config.get('context_window', 'не указан')}"
            )
            print(f"  - d_model: {model_config.get('d_model', 'не указан')}")
            print(f"  - n_heads: {model_config.get('n_heads', 'не указан')}")
            print(f"  - e_layers: {model_config.get('e_layers', 'не указан')}")

    # 4. Проверяем метрики обучения
    if "best_metrics" in checkpoint:
        metrics = checkpoint["best_metrics"]
        print("\n📊 Метрики обучения:")
        if "direction_accuracy" in metrics:
            dir_acc = metrics["direction_accuracy"]
            print("  - Direction accuracy по таймфреймам:")
            if isinstance(dir_acc, dict):
                for tf, acc in dir_acc.items():
                    print(f"    • {tf}: {acc:.1%}")
            else:
                print(f"    • Общая: {dir_acc:.1%}")

    # 5. Проверяем выходной слой для направлений
    print("\n🔍 Анализ выходных слоев:")
    state_dict = checkpoint["model_state_dict"]

    # Ищем слои связанные с direction
    direction_layers = [k for k in state_dict.keys() if "direction" in k.lower()]
    if direction_layers:
        print("  Direction слои найдены:")
        for layer_name in direction_layers[:5]:  # Показываем первые 5
            layer_shape = state_dict[layer_name].shape
            print(f"    • {layer_name}: shape={layer_shape}")

    # Ищем финальный слой
    final_layers = [
        k
        for k in state_dict.keys()
        if "final" in k.lower() or "head" in k.lower() or "output" in k.lower()
    ]
    if final_layers:
        print("\n  Финальные слои:")
        for layer_name in final_layers[:5]:
            layer_shape = state_dict[layer_name].shape
            print(f"    • {layer_name}: shape={layer_shape}")

    # 6. Проверяем, как модель была обучена
    print("\n📚 Информация об обучении:")

    # Проверяем путь к проекту обучения
    training_project = Path("/mnt/SSD/PYCHARMPRODJECT/LLM TRANSFORM/crypto_ai_trading")
    print(f"  Проект обучения: {training_project}")
    print(f"  Существует: {'✅' if training_project.exists() else '❌'}")

    # Читаем конфигурацию обучения если есть
    training_config = training_project / "config.yaml"
    if training_config.exists():
        print(f"  Конфигурация обучения найдена: {training_config}")

    print("\n" + "=" * 60)
    print("📝 ВЫВОДЫ:")
    print("=" * 60)

    print(
        """
1. КОДИРОВКА КЛАССОВ В ОБУЧЕНИИ:
   - LONG = 0
   - SHORT = 1
   - NEUTRAL/FLAT = 2

2. ТЕКУЩАЯ ИНТЕРПРЕТАЦИЯ В BOT_AI_V3:
   - weighted_direction < 0.8 → LONG
   - 0.8 <= weighted_direction < 1.2 → SHORT
   - weighted_direction >= 1.2 → NEUTRAL

3. ПРОБЛЕМА:
   Модель выдает почти равные вероятности для всех классов (~33% каждый),
   что означает крайне низкую уверенность в предсказаниях.

4. ВОЗМОЖНЫЕ ПРИЧИНЫ:
   - Модель недообучена или переобучена
   - Неправильная нормализация входных данных
   - Несоответствие признаков между обучением и inference
   - Модель требует дообучения на новых данных
    """
    )


if __name__ == "__main__":
    check_model()
