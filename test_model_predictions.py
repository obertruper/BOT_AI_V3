#!/usr/bin/env python3
"""
Тестирование предсказаний модели с реальными данными
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))


async def test_predictions():
    """Тест предсказаний модели"""

    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ПРЕДСКАЗАНИЙ МОДЕЛИ")
    print("=" * 60)

    # 1. Инициализируем ML Manager
    from core.config.config_manager import ConfigManager
    from ml.ml_manager import MLManager

    config_manager = ConfigManager()
    config = {
        "ml": config_manager.get_ml_config(),
        "system": config_manager.get_system_config(),
        "trading": config_manager.get_config("trading", {}),
    }

    print("\n1️⃣ Инициализация ML Manager...")
    ml_manager = MLManager(config)
    await ml_manager.initialize()
    print("✅ ML Manager инициализирован")

    # 2. Получаем реальные данные из БД
    from database.connections.postgres import AsyncPGPool

    # AsyncPGPool инициализируется автоматически при первом использовании

    print("\n2️⃣ Загрузка данных из БД...")

    # Берем данные для BTCUSDT за последние 24 часа
    candles = await AsyncPGPool.fetch(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM raw_market_data
        WHERE symbol = 'BTCUSDT'
        AND timestamp > NOW() - INTERVAL '24 hours'
        ORDER BY timestamp DESC
        LIMIT 96
    """
    )

    if len(candles) < 96:
        print(f"⚠️ Недостаточно данных: {len(candles)} свечей")
        return

    # Конвертируем в DataFrame
    df = pd.DataFrame(candles)
    df = df.sort_values("timestamp")  # Сортируем по времени
    df["symbol"] = "BTCUSDT"

    print(f"✅ Загружено {len(df)} свечей для BTCUSDT")

    # 3. Делаем предсказание
    print("\n3️⃣ Делаем предсказание...")

    try:
        prediction = await ml_manager.predict(df)

        print("\n📊 РЕЗУЛЬТАТЫ ПРЕДСКАЗАНИЯ:")
        print("-" * 40)
        print(f"Signal type: {prediction['signal_type']}")
        print(f"Confidence: {prediction['confidence']:.1%}")
        print(f"Signal strength: {prediction['signal_strength']:.3f}")
        print(f"Risk level: {prediction['risk_level']}")

        if "predictions" in prediction:
            pred = prediction["predictions"]
            print(f"\nDirection score: {pred['direction_score']:.3f}")
            print(f"Directions by timeframe: {pred['directions_by_timeframe']}")

            # Показываем вероятности для каждого таймфрейма
            print("\n🎯 Вероятности по таймфреймам:")
            probs = pred["direction_probabilities"]
            timeframes = ["15m", "1h", "4h", "12h"]
            for i, tf in enumerate(timeframes):
                p = probs[i]
                print(f"  {tf}: LONG={p[0]:.1%}, SHORT={p[1]:.1%}, NEUTRAL={p[2]:.1%}")

            # Анализ проблемы
            print("\n⚠️ АНАЛИЗ ПРОБЛЕМЫ:")

            # Проверяем энтропию (неуверенность)
            for i, tf in enumerate(timeframes):
                p = np.array(probs[i])
                # Энтропия Шеннона
                entropy = -np.sum(p * np.log(p + 1e-10))
                max_entropy = np.log(3)  # Максимальная энтропия для 3 классов
                uncertainty = (
                    entropy / max_entropy
                )  # Нормализованная неуверенность (0-1)
                print(f"  {tf}: неуверенность = {uncertainty:.1%}")

            # Если все вероятности близки к 33%, это признак проблемы
            all_probs = np.array(probs).flatten()
            if np.all(np.abs(all_probs - 0.333) < 0.05):
                print("\n❌ КРИТИЧЕСКАЯ ПРОБЛЕМА:")
                print("  Модель выдает почти равные вероятности для всех классов!")
                print("  Это означает, что модель по сути случайно угадывает.")
                print("\n  Возможные причины:")
                print("  1. Модель не была правильно обучена")
                print(
                    "  2. Входные признаки не соответствуют тем, на которых обучалась модель"
                )
                print("  3. Проблемы с нормализацией данных (scaler)")
                print("  4. Модель находится в режиме 'случайных' предсказаний")

    except Exception as e:
        print(f"❌ Ошибка при предсказании: {e}")
        import traceback

        traceback.print_exc()

    # 4. Проверяем scaler
    print("\n4️⃣ Проверка scaler...")

    if ml_manager.scaler is not None:
        print(f"Scaler тип: {type(ml_manager.scaler).__name__}")

        # Генерируем тестовые данные
        test_features = np.random.randn(96, 240)  # 96 временных точек, 240 признаков

        # Нормализуем
        normalized = ml_manager.scaler.transform(test_features)

        print(
            f"До нормализации: mean={test_features.mean():.3f}, std={test_features.std():.3f}"
        )
        print(
            f"После нормализации: mean={normalized.mean():.3f}, std={normalized.std():.3f}"
        )

        # Проверяем, что scaler правильно работает
        if np.abs(normalized.mean()) > 0.1 or np.abs(normalized.std() - 1.0) > 0.1:
            print(
                "⚠️ Возможна проблема с scaler - данные не стандартизированы правильно"
            )

    await AsyncPGPool.close()

    print("\n" + "=" * 60)
    print("РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    print(
        """
1. Модель выдает слишком неуверенные предсказания (все классы ~33%)
2. Это указывает на проблемы с обучением или интеграцией
3. Рекомендуется:
   - Проверить соответствие признаков между обучением и inference
   - Убедиться, что используется правильный scaler
   - Возможно, переобучить модель на актуальных данных
   - Проверить качество входных данных
    """
    )


if __name__ == "__main__":
    asyncio.run(test_predictions())
