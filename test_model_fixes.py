#!/usr/bin/env python3
"""
Тестирование исправлений модели
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))


async def test_model_fixes():
    """Тест исправленной модели с новыми порогами"""

    print("=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ МОДЕЛИ")
    print("=" * 70)

    # 1. Инициализируем ML Manager
    from core.config.config_manager import ConfigManager
    from ml.ml_manager import MLManager

    config_manager = ConfigManager()
    config = {
        "ml": config_manager.get_ml_config(),
        "system": config_manager.get_system_config(),
        "trading": config_manager.get_config("trading", {}),
    }

    print("\n1️⃣ Инициализация ML Manager с новым feature_engineering_training...")
    ml_manager = MLManager(config)
    await ml_manager.initialize()
    print("✅ ML Manager инициализирован")

    # 2. Проверяем feature engineering
    print("\n2️⃣ Проверка feature engineering...")
    from ml.logic.feature_engineering import FeatureEngineer

    fe = FeatureEngineer(config)
    # У оригинального feature_engineering нет атрибута feature_names
    print("   Feature engineering инициализирован")
    # Проверим что генерирует 240 признаков с тестовыми данными

    test_df = pd.DataFrame(
        {
            "open": np.random.randn(100) + 100,
            "high": np.random.randn(100) + 101,
            "low": np.random.randn(100) + 99,
            "close": np.random.randn(100) + 100,
            "volume": np.random.randn(100) + 1000,
            "symbol": ["TEST"] * 100,
            "datetime": pd.date_range("2024-01-01", periods=100, freq="15min"),
        }
    )
    test_features = fe.create_features(test_df)
    assert test_features.shape[1] == 240, (
        f"Ошибка: ожидалось 240, получено {test_features.shape[1]}"
    )
    print("✅ Feature engineering корректный: 240 признаков")

    # 3. Получаем данные из БД
    from database.connections.postgres import AsyncPGPool

    print("\n3️⃣ Загрузка данных из БД...")

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    for symbol in symbols:
        print(f"\n--- Тестирование {symbol} ---")

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
            print(f"⚠️ Недостаточно данных для {symbol}: {len(candles)} свечей")
            continue

        # Конвертируем в DataFrame
        df = pd.DataFrame([dict(row) for row in candles])
        df = df.sort_values("timestamp")
        df["symbol"] = symbol

        print(f"✅ Загружено {len(df)} свечей")

        # 4. Генерируем признаки
        print("   Генерация признаков...")
        features = fe.create_features(df)

        print(f"   Сгенерировано признаков: {features.shape[1]}")

        # Берем последние 96 строк
        if len(features) >= 96:
            features_for_pred = features.iloc[-96:].values
        else:
            # Padding если недостаточно данных
            padding = np.zeros((96 - len(features), 240))
            features_for_pred = np.vstack([padding, features.values])

        print(f"   Shape для предсказания: {features_for_pred.shape}")

        # 5. Делаем предсказание
        print("   Делаем предсказание...")
        prediction = await ml_manager.predict(features_for_pred)

        print(f"\n📊 РЕЗУЛЬТАТ ДЛЯ {symbol}:")
        print(f"   Signal type: {prediction['signal_type']}")
        print(f"   Confidence: {prediction['confidence']:.1%}")
        print(f"   Signal strength: {prediction['signal_strength']:.3f}")

        if "predictions" in prediction:
            pred = prediction["predictions"]
            print(f"   Direction score: {pred['direction_score']:.3f}")
            print(f"   Directions: {pred['directions_by_timeframe']}")

            # Анализ вероятностей
            probs = pred["direction_probabilities"]
            print("\n   Вероятности по таймфреймам:")
            timeframes = ["15m", "1h", "4h", "12h"]

            for i, tf in enumerate(timeframes):
                p = probs[i]
                max_idx = np.argmax(p)
                max_class = ["LONG", "SHORT", "NEUTRAL"][max_idx]
                print(
                    f"     {tf}: {max_class} ({p[max_idx]:.1%}) - L:{p[0]:.1%}, S:{p[1]:.1%}, N:{p[2]:.1%}"
                )

            # Проверяем разнообразие
            all_probs = np.array(probs).flatten()
            prob_std = np.std(all_probs)
            prob_range = np.max(all_probs) - np.min(all_probs)

            print("\n   📈 Анализ качества:")
            print(f"     Std вероятностей: {prob_std:.3f}")
            print(f"     Разброс: {prob_range:.3f}")

            if prob_std > 0.15:
                print("     ✅ Модель выдает разнообразные предсказания")
            else:
                print("     ⚠️ Модель неуверенная (низкий std)")

    await AsyncPGPool.close()

    print("\n" + "=" * 70)
    print("📝 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("=" * 70)

    print(
        """
Проверьте результаты выше:

✅ УСПЕХ если:
- Feature engineering генерирует ровно 240 признаков
- Есть разные типы сигналов (не только NEUTRAL)
- Вероятности НЕ равны ~33% для всех классов
- Std вероятностей > 0.15

❌ ПРОБЛЕМА если:
- Все сигналы NEUTRAL
- Все вероятности ~33%
- Direction score всегда ~1.3-1.6

Если проблемы остаются:
1. Проверить актуальность данных в БД
2. Проверить версии библиотек (особенно ta)
3. Возможно нужно переобучить модель
    """
    )


if __name__ == "__main__":
    asyncio.run(test_model_fixes())
