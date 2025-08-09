#!/usr/bin/env python3
"""
Быстрая проверка что ML больше не возвращает только FLAT.
"""

import asyncio
import sys

import numpy as np

sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from core.config.config_manager import ConfigManager
from core.logger import setup_logger
from ml.ml_manager import MLManager

logger = setup_logger(__name__)


async def quick_ml_check():
    """Быстрая проверка ML предсказаний."""

    print("⚡ Quick ML Check...")

    config_manager = ConfigManager()
    config = config_manager.get_config()
    ml_manager = MLManager(config)

    if not await ml_manager.initialize():
        print("❌ ML Manager initialization failed")
        return

    print("✅ ML Manager initialized")

    # Тестируем с разными входными данными
    test_cases = [
        ("Random Normal", np.random.randn(1, 96, 240).astype(np.float32)),
        ("Small Values", np.random.randn(1, 96, 240).astype(np.float32) * 0.1),
        ("Large Values", np.random.randn(1, 96, 240).astype(np.float32) * 10),
        ("Trend Up", create_trend_data(1.0)),
        ("Trend Down", create_trend_data(-1.0)),
    ]

    results = []

    print("\n📊 Testing different inputs:")
    for name, test_input in test_cases:
        print(f"\n  Testing: {name}")

        try:
            prediction = await ml_manager.predict(test_input)

            if prediction and "predictions" in prediction:
                pred_array = prediction["predictions"]

                # Извлекаем направления (предполагаем индексы 4-7)
                if len(pred_array) >= 8:
                    directions = pred_array[4:8]
                    print(f"    Raw predictions: {pred_array[:8]}")
                    print(f"    Directions: {directions}")

                    # Анализируем уникальность
                    unique_dirs = np.unique(directions)
                    print(f"    Unique directions: {unique_dirs}")

                    results.append(
                        {
                            "name": name,
                            "directions": directions,
                            "unique_count": len(unique_dirs),
                        }
                    )
                else:
                    print(f"    Error: prediction array too short: {len(pred_array)}")
            else:
                print("    Error: No predictions in result")

        except Exception as e:
            print(f"    Error: {e}")

    # Анализ результатов
    print("\n📈 Summary:")
    if results:
        all_directions = []
        for r in results:
            all_directions.extend(r["directions"])

        unique_overall = np.unique(all_directions)
        print(f"  Total tests: {len(results)}")
        print(f"  Unique directions overall: {unique_overall}")

        # Проверяем разнообразие
        all_same = all(r["unique_count"] == 1 for r in results)

        if all_same and len(unique_overall) == 1:
            print("❌ ISSUE: All predictions show the same direction!")
            print(f"   Constant value: {unique_overall[0]}")
        elif len(unique_overall) == 1:
            print("⚠️  WARNING: Low diversity in predictions")
        else:
            print("✅ SUCCESS: Model generates diverse predictions!")
    else:
        print("❌ No successful predictions")


def create_trend_data(trend):
    """Создает данные с трендом."""
    data = np.random.randn(1, 96, 240).astype(np.float32) * 0.1

    # Добавляем тренд в первые features
    for i in range(96):
        trend_value = trend * i / 96
        data[0, i, 0] += trend_value  # Close price
        data[0, i, 1] += trend_value * 0.9  # Open price

    return data


if __name__ == "__main__":
    asyncio.run(quick_ml_check())
