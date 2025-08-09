#!/usr/bin/env python3
"""
Анализ и исправление проблемы с ML предсказаниями
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).parent))

from core.logger import setup_logger
from ml.logic.feature_engineering import FeatureEngineer

logger = setup_logger("fix_ml")


def analyze_features():
    """Анализ генерируемых признаков"""

    print("🔍 Анализ системы генерации признаков...")

    # Создаем тестовые данные
    np.random.seed(42)
    n_candles = 300

    # Генерируем разнообразные данные
    timestamps = pd.date_range(end=pd.Timestamp.now(), periods=n_candles, freq="15min")

    # Создаем три разных сценария
    scenarios = {
        "uptrend": {
            "trend": np.linspace(100000, 105000, n_candles),  # +5%
            "noise": np.random.normal(0, 100, n_candles),
        },
        "downtrend": {
            "trend": np.linspace(100000, 95000, n_candles),  # -5%
            "noise": np.random.normal(0, 100, n_candles),
        },
        "sideways": {
            "trend": np.full(n_candles, 100000),
            "noise": np.random.normal(0, 500, n_candles),
        },
    }

    fe = FeatureEngineer({})

    for scenario_name, scenario_data in scenarios.items():
        print(f"\n📊 Сценарий: {scenario_name}")

        prices = scenario_data["trend"] + scenario_data["noise"]

        data = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": prices * (1 + np.random.uniform(-0.001, 0.001, n_candles)),
                "high": prices * (1 + np.random.uniform(0, 0.002, n_candles)),
                "low": prices * (1 - np.random.uniform(0, 0.002, n_candles)),
                "close": prices,
                "volume": np.random.uniform(100, 1000, n_candles),
                "symbol": "BTCUSDT",
            }
        )

        # Генерируем признаки
        features = fe.create_features(data)

        print(f"  Shape: {features.shape}")
        print("  Средние значения первых 10 признаков:")
        for i in range(min(10, features.shape[1])):
            mean_val = np.mean(features[:, i])
            std_val = np.std(features[:, i])
            print(f"    Feature {i}: mean={mean_val:.4f}, std={std_val:.4f}")

        # Проверяем на константные признаки
        constant_features = []
        for i in range(features.shape[1]):
            if np.std(features[:, i]) < 0.0001:
                constant_features.append(i)

        if constant_features:
            print(
                f"  ⚠️ Найдено {len(constant_features)} константных признаков: {constant_features[:10]}..."
            )

        # Проверяем на NaN/Inf
        nan_count = np.isnan(features).sum()
        inf_count = np.isinf(features).sum()

        if nan_count > 0:
            print(f"  ⚠️ Найдено {nan_count} NaN значений")
        if inf_count > 0:
            print(f"  ⚠️ Найдено {inf_count} Inf значений")


def test_model_outputs():
    """Тест выходов модели напрямую"""

    print("\n🧪 Тест выходов модели...")

    # Загружаем модель
    from ml.logic.patchtst_model import create_unified_model

    config = {
        "model": {
            "input_size": 240,
            "output_size": 20,
            "context_window": 96,
            "patch_len": 16,
            "stride": 8,
            "d_model": 256,
            "n_heads": 4,
            "e_layers": 3,
            "d_ff": 512,
            "dropout": 0.1,
        }
    }

    model = create_unified_model(config)
    checkpoint = torch.load(
        "models/saved/best_model_20250728_215703.pth", map_location="cpu"
    )
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Тестируем с разными входами
    test_inputs = [
        torch.randn(1, 96, 240),  # Случайный
        torch.zeros(1, 96, 240),  # Нули
        torch.ones(1, 96, 240),  # Единицы
        torch.randn(1, 96, 240) * 10,  # Большие значения
    ]

    print("\nВыходы модели для разных входов:")
    with torch.no_grad():
        for i, x in enumerate(test_inputs):
            outputs = model(x)
            outputs_np = outputs.numpy()[0]

            # Анализируем future_directions (индексы 4-7)
            future_directions = outputs_np[4:8]

            print(f"\nВход {i + 1}:")
            print(f"  Future directions: {future_directions}")
            print(f"  После tanh: {np.tanh(future_directions)}")

            # Проверяем другие выходы
            print(f"  Future returns (0-3): {outputs_np[0:4]}")
            print(f"  Level targets (8-15): {outputs_np[8:16]}")
            print(f"  Risk metrics (16-19): {outputs_np[16:20]}")


def compare_with_llm_transform():
    """Сравнение с LLM TRANSFORM реализацией"""

    print("\n📋 Ключевые различия с LLM TRANSFORM:")

    differences = """
    1. BOT_AI_V3 использует StandardScaler вместо RobustScaler
       - StandardScaler чувствителен к выбросам
       - RobustScaler использует медиану и IQR

    2. BOT_AI_V3 не имеет индивидуальных скейлеров по символам
       - Один скейлер для всех данных
       - В LLM TRANSFORM - отдельный для каждого символа

    3. Отсутствуют crypto-специфичные признаки:
       - Funding rates
       - Liquidation levels
       - Cross-asset correlations
       - Market microstructure

    4. Нет walk-forward validation
       - Возможна утечка данных из будущего
       - В LLM TRANSFORM строгое временное разделение

    5. Упрощенная обработка выбросов
       - Нет клиппинга экстремальных значений
       - Нет безопасного деления с обработкой inf/nan
    """

    print(differences)

    print("\n✅ Рекомендации:")
    print("1. Скопировать feature_engineering.py из LLM TRANSFORM")
    print("2. Заменить модель и scaler на версии из LLM TRANSFORM")
    print("3. Обновить логику интерпретации предсказаний")
    print("4. Добавить валидацию входных данных")


if __name__ == "__main__":
    print("=" * 60)
    print("АНАЛИЗ ПРОБЛЕМЫ ML ПРЕДСКАЗАНИЙ")
    print("=" * 60)

    # Анализируем признаки
    analyze_features()

    # Тестируем модель
    test_model_outputs()

    # Сравниваем с эталоном
    compare_with_llm_transform()

    print("\n" + "=" * 60)
    print("ВЫВОД: Необходимо перенести feature engineering из LLM TRANSFORM")
    print("=" * 60)
