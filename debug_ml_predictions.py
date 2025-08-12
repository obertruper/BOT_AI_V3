#!/usr/bin/env python3
"""
Детальная диагностика ML предсказаний
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))


async def debug_predictions():
    """Анализ проблем с предсказаниями модели"""

    print("=" * 80)
    print("🔍 ДИАГНОСТИКА ML ПРЕДСКАЗАНИЙ")
    print("=" * 80)

    from core.config.config_manager import ConfigManager
    from database.connections.postgres import AsyncPGPool
    from ml.ml_manager import MLManager

    config_manager = ConfigManager()
    config = {
        "ml": config_manager.get_ml_config(),
        "system": config_manager.get_system_config(),
        "trading": config_manager.get_config("trading", {}),
    }

    ml_manager = MLManager(config)
    await ml_manager.initialize()

    # Тестируем на разных символах
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    all_predictions = []

    for symbol in symbols:
        print(f"\n📊 Анализ {symbol}...")

        # Получаем данные
        candles = await AsyncPGPool.fetch(
            """
            SELECT timestamp, open, high, low, close, volume
            FROM raw_market_data
            WHERE symbol = $1
            ORDER BY timestamp DESC
            LIMIT 200
        """,
            symbol,
        )

        if len(candles) < 96:
            print(f"⚠️ Недостаточно данных для {symbol}")
            continue

        df = pd.DataFrame([dict(row) for row in candles])
        df = df.sort_values("timestamp")
        df["symbol"] = symbol

        # Генерируем признаки
        from ml.logic.feature_engineering_training import FeatureEngineer

        fe = FeatureEngineer(config)
        features = fe.create_features(df)

        # Проверяем признаки
        print(f"   Сгенерировано признаков: {features.shape}")

        # Анализ признаков
        # Конвертируем в numpy для анализа
        features_np = features.values.astype(np.float64)
        zero_variance_cols = (np.std(features_np, axis=0) < 1e-6).sum()
        nan_cols = np.isnan(features_np).any(axis=0).sum()
        inf_cols = np.isinf(features_np).any(axis=0).sum()

        print("   📈 Статистика признаков:")
        print(f"      Нулевая дисперсия: {zero_variance_cols}/{features.shape[1]}")
        print(f"      Колонки с NaN: {nan_cols}")
        print(f"      Колонки с Inf: {inf_cols}")

        # Проверяем конкретные признаки
        if zero_variance_cols > 0:
            std_by_col = np.std(features_np, axis=0)
            zero_var_indices = np.where(std_by_col < 1e-6)[0][:10]
            zero_var_names = [features.columns[i] for i in zero_var_indices]
            print(f"      Примеры нулевой дисперсии: {zero_var_names}")

        # Подготавливаем для модели
        if len(features) >= 96:
            features_for_pred = features.iloc[-96:].values
        else:
            padding = np.zeros((96 - len(features), 240))
            features_for_pred = np.vstack([padding, features.values])

        # Делаем предсказание
        prediction = await ml_manager.predict(features_for_pred)
        all_predictions.append(
            {
                "symbol": symbol,
                "signal_type": prediction["signal_type"],
                "confidence": prediction["confidence"],
                "directions": prediction["predictions"]["directions_by_timeframe"],
                "probs": prediction["predictions"]["direction_probabilities"],
            }
        )

        print("\n   🎯 РЕЗУЛЬТАТ:")
        print(f"      Signal: {prediction['signal_type']}")
        print(f"      Confidence: {prediction['confidence']:.1%}")
        print(
            f"      Directions: {prediction['predictions']['directions_by_timeframe']}"
        )

        # Анализ вероятностей
        probs = np.array(prediction["predictions"]["direction_probabilities"])
        print("\n   📊 Анализ вероятностей:")
        for i, tf in enumerate(["15m", "1h", "4h", "12h"]):
            p = probs[i]
            print(f"      {tf}: LONG={p[0]:.3f}, SHORT={p[1]:.3f}, NEUTRAL={p[2]:.3f}")

        # Проверяем логиты модели
        print("\n   🔬 Диагностика модели:")
        print(
            f"      Direction score: {prediction['predictions']['direction_score']:.3f}"
        )
        print(f"      Returns 15m: {prediction['predictions']['returns_15m']:.6f}")
        print(f"      Returns 1h: {prediction['predictions']['returns_1h']:.6f}")
        print(f"      Returns 4h: {prediction['predictions']['returns_4h']:.6f}")
        print(f"      Returns 12h: {prediction['predictions']['returns_12h']:.6f}")

    await AsyncPGPool.close()

    # Анализ паттернов
    print("\n" + "=" * 80)
    print("📊 АНАЛИЗ ПАТТЕРНОВ")
    print("=" * 80)

    if all_predictions:
        # Проверяем уникальность directions
        all_directions = [str(p["directions"]) for p in all_predictions]
        unique_directions = set(all_directions)

        print("\n🔍 Уникальность паттернов направлений:")
        print(f"   Всего предсказаний: {len(all_predictions)}")
        print(f"   Уникальных паттернов: {len(unique_directions)}")
        print(f"   Паттерны: {unique_directions}")

        # Проверяем распределение классов
        all_probs = []
        for p in all_predictions:
            all_probs.extend(p["probs"])

        all_probs = np.array(all_probs)

        print("\n📈 Распределение вероятностей:")
        print(f"   Mean LONG: {all_probs[:, 0].mean():.3f}")
        print(f"   Mean SHORT: {all_probs[:, 1].mean():.3f}")
        print(f"   Mean NEUTRAL: {all_probs[:, 2].mean():.3f}")
        print(f"   Std всех вероятностей: {all_probs.std():.3f}")

        # Проверяем дисбаланс
        if all_probs[:, 2].mean() > 0.5:
            print("\n⚠️ ПРОБЛЕМА: Модель смещена к NEUTRAL классу!")
            print("   Возможные причины:")
            print("   1. Модель переобучена на NEUTRAL")
            print("   2. Признаки не информативны (много нулевой дисперсии)")
            print("   3. Данные для обучения были несбалансированы")

    print("\n" + "=" * 80)
    print("💡 РЕКОМЕНДАЦИИ")
    print("=" * 80)

    print(
        """
1. КРИТИЧНО: 222 из 240 признаков имеют нулевую дисперсию
   → Это означает что feature engineering не работает правильно
   → Нужно исправить расчет индикаторов

2. Модель смещена к NEUTRAL
   → Паттерн [2,1,2,1] повторяется для всех символов
   → Нужно проверить обученную модель или переобучить

3. Следующие шаги:
   a) Исправить feature engineering (убрать константные признаки)
   b) Проверить версию модели (возможно загружена не та)
   c) Изменить пороги для более агрессивной торговли
"""
    )


if __name__ == "__main__":
    asyncio.run(debug_predictions())
