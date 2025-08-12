#!/usr/bin/env python3
"""
Быстрый тест исправлений ML системы
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import torch

# Добавляем корень проекта в путь
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config.config_manager import ConfigManager
from ml.ml_manager import MLManager


async def test_ml_fixes():
    """
    Тестирует исправления в ML системе
    """
    print("🔧 ТЕСТ ИСПРАВЛЕНИЙ ML СИСТЕМЫ")
    print("=" * 40)

    try:
        # Инициализация
        config_manager = ConfigManager()
        config = config_manager.get_config()

        ml_manager = MLManager(config)
        await ml_manager.initialize()

        print("✅ ML Manager инициализирован")
        print(f"💻 Device: {ml_manager.device}")

        # Тестируем прямое предсказание модели
        print("\n🧠 Тестирование модели:")

        device = ml_manager.device
        test_input = torch.randn(1, 96, 240).to(device)

        ml_manager.model.eval()
        with torch.no_grad():
            raw_output = ml_manager.model(test_input)

        print(f"📊 Выход модели: {raw_output.shape}")

        # Тестируем интерпретацию
        prediction = ml_manager._interpret_predictions(raw_output)

        print("\n📈 РЕЗУЛЬТАТ ИНТЕРПРЕТАЦИИ:")
        print(f"🎯 Signal type: {prediction['signal_type']}")
        print(f"📊 Confidence: {prediction['confidence']:.4f}")
        print(f"📊 Signal strength: {prediction['signal_strength']:.4f}")

        predictions_data = prediction.get("predictions", {})
        directions = predictions_data.get("directions_by_timeframe", [])
        direction_probs = predictions_data.get("direction_probabilities", [])

        print("\n🎯 Детальный анализ:")
        print(f"📊 Directions: {directions}")

        if direction_probs:
            for i, probs in enumerate(direction_probs):
                timeframe = ["15m", "1h", "4h", "12h"][i] if i < 4 else f"{i}"
                class_names = ["LONG", "SHORT", "NEUTRAL"]
                predicted_class = np.argmax(probs)
                print(
                    f"   {timeframe}: {class_names[predicted_class]} (p={probs[predicted_class]:.3f})"
                )

        # Проверяем несколько тестов подряд для разнообразия
        print("\n🔄 Тест разнообразия (5 случайных предсказаний):")

        signal_types = []
        for i in range(5):
            test_input = torch.randn(1, 96, 240).to(device)
            with torch.no_grad():
                raw_output = ml_manager.model(test_input)
            prediction = ml_manager._interpret_predictions(raw_output)
            signal_type = prediction["signal_type"]
            confidence = prediction["confidence"]
            signal_types.append(signal_type)
            print(f"   Тест {i + 1}: {signal_type} (confidence: {confidence:.3f})")

        # Статистика разнообразия
        unique_signals = set(signal_types)
        print("\n📊 Статистика разнообразия:")
        print(f"   Уникальных типов сигналов: {len(unique_signals)} из 5")
        for signal_type in ["LONG", "SHORT", "NEUTRAL"]:
            count = signal_types.count(signal_type)
            print(f"   {signal_type}: {count}/5 ({count / 5 * 100:.1f}%)")

        if "LONG" in signal_types or "SHORT" in signal_types:
            print("✅ ИСПРАВЛЕНИЕ УСПЕШНО: Генерируются торговые сигналы!")
        else:
            print("❌ Все еще только NEUTRAL сигналы")

        print("\n✅ Тест завершен!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_ml_fixes())
