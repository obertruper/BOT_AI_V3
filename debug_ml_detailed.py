#!/usr/bin/env python3
"""
Детальная диагностика ML модели - проверка входных/выходных данных
"""

import asyncio
import json
import sys

import numpy as np
import pandas as pd
import torch

sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from ml.logic.feature_engineering import FeatureEngineer
from ml.ml_manager import MLManager

logger = setup_logger("debug_ml_detailed")


async def debug_ml_pipeline():
    """Детальная отладка ML pipeline с логированием всех этапов."""

    print("🔍 ДЕТАЛЬНАЯ ДИАГНОСТИКА ML PIPELINE\n")

    # 1. Инициализация компонентов
    print("1️⃣ Инициализация компонентов...")
    config = {
        "ml": {
            "model": {"device": "cuda" if torch.cuda.is_available() else "cpu"},
            "model_directory": "models/saved",
        }
    }

    ml_manager = MLManager(config)
    await ml_manager.initialize()

    feature_engineer = FeatureEngineer(config)

    # 2. Загрузка данных из БД
    print("\n2️⃣ Загрузка данных из БД...")
    query = """
    SELECT * FROM raw_market_data
    WHERE symbol = 'BTCUSDT'
    ORDER BY datetime DESC
    LIMIT 100
    """

    raw_data = await AsyncPGPool.fetch(query)

    if not raw_data:
        print("❌ Нет данных в БД!")
        return

    # Преобразуем в DataFrame (из asyncpg Records)
    df_data = []
    for row in raw_data:
        df_data.append(dict(row))
    df = pd.DataFrame(df_data)

    # Конвертируем Decimal в float
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df.sort_values("datetime")

    print(f"✅ Загружено {len(df)} свечей")
    print(f"   Период: {df['datetime'].min()} - {df['datetime'].max()}")
    print(f"   Цена: ${float(df['close'].iloc[-1]):.2f}")

    # 3. Генерация признаков
    print("\n3️⃣ Генерация признаков (Feature Engineering)...")

    # Генерация признаков
    features = feature_engineer.create_features(df)

    print(f"✅ Сгенерировано признаков: {features.shape}")
    print(f"   Shape: {features.shape}")
    print(f"   Min: {features.min():.6f}, Max: {features.max():.6f}")
    print(f"   Mean: {features.mean():.6f}, Std: {features.std():.6f}")

    # Проверка на NaN
    nan_count = np.isnan(features).sum()
    if nan_count > 0:
        print(f"⚠️  Обнаружено {nan_count} NaN значений!")

    # 4. Проверка scaler
    print("\n4️⃣ Проверка нормализации (Scaler)...")

    if ml_manager.scaler:
        # Берем последние 96 точек
        if len(features) >= 96:
            features_window = features[-96:]
        else:
            # Дополняем нулями
            padding = np.zeros((96 - len(features), features.shape[1]))
            features_window = np.vstack([padding, features])

        # Нормализация
        features_scaled = ml_manager.scaler.transform(features_window)

        print("✅ После нормализации:")
        print(f"   Shape: {features_scaled.shape}")
        print(f"   Min: {features_scaled.min():.6f}, Max: {features_scaled.max():.6f}")
        print(
            f"   Mean: {features_scaled.mean():.6f}, Std: {features_scaled.std():.6f}"
        )

        # Проверка первых 10 значений
        print("\n   Пример первых 10 значений (последняя точка):")
        print(f"   До: {features_window[-1, :10]}")
        print(f"   После: {features_scaled[-1, :10]}")

    # 5. Проверка модели
    print("\n5️⃣ Проверка модели...")

    # Информация о модели
    model_info = ml_manager.get_model_info()
    print(f"   Модель: {model_info['model_type']}")
    print(f"   Device: {model_info['device']}")
    print(f"   Загружена: {model_info['model_loaded']}")

    # Проверка весов модели
    if ml_manager.model:
        # Проверяем веса первого слоя
        first_layer = list(ml_manager.model.parameters())[0]
        print("\n   Веса первого слоя:")
        print(f"   Shape: {first_layer.shape}")
        print(
            f"   Min: {first_layer.min().item():.6f}, Max: {first_layer.max().item():.6f}"
        )
        print(
            f"   Mean: {first_layer.mean().item():.6f}, Std: {first_layer.std().item():.6f}"
        )

        # Проверяем, инициализированы ли веса
        if first_layer.std().item() < 0.001:
            print("   ⚠️ ВНИМАНИЕ: Веса практически нулевые - модель не обучена!")

    # 6. Прямой проход через модель
    print("\n6️⃣ Прямой проход через модель...")

    # Подготовка тензора
    x = torch.FloatTensor(features_scaled).unsqueeze(0).to(ml_manager.device)
    print(f"   Input tensor shape: {x.shape}")

    # Forward pass
    with torch.no_grad():
        # Прямой вызов модели
        raw_output = ml_manager.model(x)

        print("\n   Raw model output:")
        print(f"   Shape: {raw_output.shape}")
        print(f"   Values: {raw_output.cpu().numpy()[0]}")
        print(
            f"   Min: {raw_output.min().item():.6f}, Max: {raw_output.max().item():.6f}"
        )

    # 7. Полный predict через MLManager
    print("\n7️⃣ Полный predict через MLManager...")

    prediction = await ml_manager.predict(features_window)

    print("\n📊 Результат предсказания:")
    print(json.dumps(prediction, indent=2))

    # 8. Анализ проблемы
    print("\n8️⃣ АНАЛИЗ ПРОБЛЕМЫ:")

    # Проверка архитектуры модели
    print("\n🏗️ Архитектура модели:")
    print(ml_manager.model)

    # Проверка, есть ли обученная модель
    model_path = ml_manager.model_path
    if model_path.exists():
        print(f"\n✅ Файл модели найден: {model_path}")
        # Загружаем checkpoint
        checkpoint = torch.load(model_path, map_location="cpu")
        print(f"   Ключи в checkpoint: {list(checkpoint.keys())}")
        if "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
            print(f"   Слои в модели: {list(state_dict.keys())[:5]}...")
    else:
        print(f"\n❌ Файл модели НЕ НАЙДЕН: {model_path}")
        print("   Это объясняет почему все предсказания одинаковые!")

    # 9. Проверка интерпретации
    print("\n9️⃣ Проверка интерпретации предсказаний...")

    # Тестовые значения для проверки логики
    test_values = [
        np.array([0.0, 0.0, 0.0, 0.0]),  # Все нули
        np.array([1.0, 1.0, 1.0, 1.0]),  # Все единицы
        np.array([2.0, 2.0, 2.0, 2.0]),  # Текущая проблема
        np.array([-1.0, 0.0, 1.0, 2.0]),  # Разные значения
    ]

    print("\nТестирование интерпретации разных значений:")
    for i, test_val in enumerate(test_values):
        normalized = np.tanh(test_val)
        interpreted = []
        for norm in normalized:
            if norm > 0.2:
                interpreted.append("LONG")
            elif norm < -0.2:
                interpreted.append("SHORT")
            else:
                interpreted.append("NEUTRAL")

        print(f"\n   Test {i + 1}: {test_val}")
        print(f"   Tanh: {normalized}")
        print(f"   Интерпретация: {interpreted}")

    print("\n" + "=" * 80)
    print("📌 ВЫВОДЫ:")
    print("1. Модель всегда возвращает [2.0, 2.0, 2.0, 2.0], потому что:")
    print("   - Файл модели отсутствует или не содержит обученных весов")
    print("   - Используются случайные/неинициализированные веса")
    print("   - После tanh(2.0) = 0.964, что всегда > 0.2 → всегда LONG")
    print("\n2. Необходимо:")
    print("   - Обучить модель на реальных данных")
    print("   - Сохранить веса в правильном формате")
    print("   - Проверить процесс загрузки модели")


if __name__ == "__main__":
    asyncio.run(debug_ml_pipeline())
