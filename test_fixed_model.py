#!/usr/bin/env python3
"""
Тестирование исправленной модели с правильными признаками
"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))


async def test_fixed_model():
    """Тест исправленной модели"""

    print("=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕННОЙ МОДЕЛИ")
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

    print("\n1️⃣ Инициализация ML Manager с новым feature_engineering...")
    ml_manager = MLManager(config)
    await ml_manager.initialize()
    print("✅ ML Manager инициализирован")

    # 2. Получаем реальные данные
    from database.connections.postgres import AsyncPGPool

    print("\n2️⃣ Загрузка данных из БД...")

    # Берем данные для BTCUSDT
    candles = await AsyncPGPool.fetch(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM raw_market_data
        WHERE symbol = 'BTCUSDT'
        ORDER BY timestamp DESC
        LIMIT 200
    """
    )

    if len(candles) < 96:
        print(f"⚠️ Недостаточно данных: {len(candles)} свечей")
        return

    # Конвертируем в DataFrame
    df = pd.DataFrame(candles)
    df = df.sort_values("timestamp")
    df["symbol"] = "BTCUSDT"

    print(f"✅ Загружено {len(df)} свечей для BTCUSDT")
    print(f"   Период: {df['timestamp'].min()} - {df['timestamp'].max()}")

    # 3. Проверяем генерацию признаков
    print("\n3️⃣ Генерация признаков с новым feature_engineering_v4...")

    from ml.logic.feature_engineering_v4 import FeatureEngineer

    feature_engineer = FeatureEngineer(config)

    features = feature_engineer.create_features(df)

    print(f"✅ Сгенерировано признаков: {features.shape[1]}")
    print(f"   Строк: {features.shape[0]}")

    if features.shape[1] != 240:
        print(f"❌ ОШИБКА: Ожидалось 240 признаков, получено {features.shape[1]}")
    else:
        print("✅ Количество признаков корректное: 240")

    # Проверяем на NaN и Inf
    nan_count = features.isna().sum().sum()
    inf_count = np.isinf(features.select_dtypes(include=[np.number])).sum().sum()

    print(f"\n   NaN значений: {nan_count}")
    print(f"   Inf значений: {inf_count}")

    # 4. Делаем предсказание
    print("\n4️⃣ Делаем предсказание с исправленной моделью...")

    try:
        # Берем последние 96 строк с признаками
        if len(features) >= 96:
            features_for_prediction = features.iloc[-96:]
        else:
            print("⚠️ Недостаточно данных, дополняем нулями")
            padding = pd.DataFrame(
                0, index=range(96 - len(features)), columns=features.columns
            )
            features_for_prediction = pd.concat([padding, features], ignore_index=True)

        # Преобразуем в numpy array
        features_array = features_for_prediction.values

        print(f"   Shape для предсказания: {features_array.shape}")

        # Делаем предсказание
        prediction = await ml_manager.predict(features_array)

        print("\n📊 РЕЗУЛЬТАТЫ ПРЕДСКАЗАНИЯ:")
        print("-" * 50)
        print(f"Signal type: {prediction['signal_type']}")
        print(f"Confidence: {prediction['confidence']:.1%}")
        print(f"Signal strength: {prediction['signal_strength']:.3f}")
        print(f"Risk level: {prediction['risk_level']}")

        if "predictions" in prediction:
            pred = prediction["predictions"]
            print(f"\nDirection score: {pred['direction_score']:.3f}")
            print(f"Directions by timeframe: {pred['directions_by_timeframe']}")

            # Показываем вероятности
            print("\n🎯 Вероятности по таймфреймам:")
            probs = pred["direction_probabilities"]
            timeframes = ["15m", "1h", "4h", "12h"]

            for i, tf in enumerate(timeframes):
                p = probs[i]
                print(f"  {tf}: LONG={p[0]:.1%}, SHORT={p[1]:.1%}, NEUTRAL={p[2]:.1%}")

                # Проверяем разнообразие
                max_prob = max(p)
                if max_prob > 0.5:  # Есть явный фаворит
                    print("       → Уверенное предсказание!")
                elif max_prob < 0.4:  # Все примерно равны
                    print("       → ⚠️ Неуверенное предсказание")

            # Анализ улучшений
            print("\n📈 АНАЛИЗ КАЧЕСТВА ПРЕДСКАЗАНИЙ:")

            all_probs = np.array(probs).flatten()
            prob_std = np.std(all_probs)
            prob_range = np.max(all_probs) - np.min(all_probs)

            print(f"   Стандартное отклонение вероятностей: {prob_std:.3f}")
            print(f"   Разброс вероятностей: {prob_range:.3f}")

            if prob_std > 0.15:
                print("   ✅ Модель выдает разнообразные предсказания")
            else:
                print("   ⚠️ Модель все еще неуверенная")

            # Проверяем согласованность по таймфреймам
            directions = pred["directions_by_timeframe"]
            unique_directions = len(set(directions))

            print(f"\n   Уникальных направлений: {unique_directions} из 4")
            if unique_directions == 1:
                print("   ✅ Все таймфреймы согласны - сильный сигнал!")
            elif unique_directions == 4:
                print("   ⚠️ Все таймфреймы разные - слабый сигнал")

    except Exception as e:
        print(f"❌ Ошибка при предсказании: {e}")
        import traceback

        traceback.print_exc()

    # 5. Проверяем нормализацию
    print("\n5️⃣ Проверка нормализации данных...")

    if ml_manager.scaler is not None:
        print(f"Scaler тип: {type(ml_manager.scaler).__name__}")

        # Нормализуем признаки
        try:
            features_normalized = ml_manager.scaler.transform(features_array)

            print("После нормализации (RobustScaler):")
            print(f"  Median: {np.median(features_normalized):.4f}")
            print(
                f"  IQR: {np.percentile(features_normalized, 75) - np.percentile(features_normalized, 25):.4f}"
            )
            print(f"  Min: {features_normalized.min():.4f}")
            print(f"  Max: {features_normalized.max():.4f}")

            # RobustScaler должен центрировать данные вокруг 0 с IQR ~1
            if abs(np.median(features_normalized)) < 0.1:
                print("  ✅ Нормализация корректная")
            else:
                print("  ⚠️ Возможна проблема с нормализацией")

        except Exception as e:
            print(f"❌ Ошибка нормализации: {e}")

    await AsyncPGPool.close()

    print("\n" + "=" * 70)
    print("📝 ИТОГИ ТЕСТИРОВАНИЯ:")
    print("=" * 70)
    print(
        """
Проверьте результаты выше:

✅ УСПЕХ если:
- Генерируется ровно 240 признаков
- Вероятности НЕ равны ~33% для всех классов
- Есть явные фавориты в предсказаниях (>50%)
- Стандартное отклонение вероятностей > 0.15

❌ ПРОБЛЕМА если:
- Количество признаков != 240
- Все вероятности ~33%
- Модель неуверенная во всех предсказаниях

Если проблемы остаются, возможно нужно:
1. Переобучить модель с новыми данными
2. Проверить версии библиотек (pandas, numpy, ta)
3. Убедиться что данные актуальные
    """
    )


if __name__ == "__main__":
    asyncio.run(test_fixed_model())
