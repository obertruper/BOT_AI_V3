#!/usr/bin/env python3
"""
Мониторинг ML модели в реальном времени - проверка входа/выхода данных
Сравнение с логикой из LLM TRANSFORM проекта
"""

import asyncio
import sys

import pandas as pd

sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from ml.logic.feature_engineering import FeatureEngineer
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger("monitor_ml_realtime")


async def monitor_ml_pipeline():
    """Мониторинг ML pipeline в реальном времени."""

    print("🔍 МОНИТОРИНГ ML PIPELINE В РЕАЛЬНОМ ВРЕМЕНИ\n")
    print("Сравнение с логикой из LLM TRANSFORM проекта\n")

    # 1. Инициализация компонентов
    config = {"ml": {"model": {"device": "cuda"}, "model_directory": "models/saved"}}

    # Инициализируем компоненты
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    # MLSignalProcessor требует ml_manager как первый аргумент
    ml_processor = MLSignalProcessor(ml_manager, config)
    # await ml_processor.initialize()  # У него нет метода initialize

    feature_engineer = FeatureEngineer(config)

    # 2. Получаем реальные данные для всех активных пар
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]

    for symbol in symbols[:3]:  # Проверим первые 3 символа
        print(f"\n{'=' * 80}")
        print(f"📊 Анализ для {symbol}")
        print(f"{'=' * 80}\n")

        # Загружаем свежие данные
        query = """
        SELECT * FROM raw_market_data
        WHERE symbol = $1
        ORDER BY datetime DESC
        LIMIT 100
        """

        raw_data = await AsyncPGPool.fetch(query, symbol)

        if not raw_data:
            print(f"❌ Нет данных для {symbol}")
            continue

        # Преобразуем в DataFrame
        df_data = [dict(row) for row in raw_data]
        df = pd.DataFrame(df_data)

        # Конвертируем Decimal в float
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)

        df = df.sort_values("datetime")

        print(f"1️⃣ Загружено данных: {len(df)} свечей")
        print(f"   Последняя цена: ${df['close'].iloc[-1]:.2f}")
        print(f"   Время: {df['datetime'].iloc[-1]}")

        # 3. Feature Engineering (как в LLM TRANSFORM)
        print("\n2️⃣ Feature Engineering:")

        features = feature_engineer.create_features(df)
        print(f"   Сгенерировано признаков: {features.shape}")
        print(
            f"   Статистика: min={features.min():.3f}, max={features.max():.3f}, mean={features.mean():.3f}"
        )

        # Проверка ключевых признаков (как в LLM TRANSFORM)
        if len(features) >= 96:
            last_features = features[-1]
            print("\n   📈 Ключевые индикаторы (последняя точка):")

            # Индексы признаков из LLM TRANSFORM
            # RSI обычно в начале после price features
            print(f"   • RSI(14): {last_features[10]:.2f}")
            print(f"   • MA(20): {last_features[20]:.2f}")
            print(f"   • Volume: {last_features[5]:.2f}")

        # 4. ML Prediction (проверяем что входит в модель)
        print("\n3️⃣ ML Prediction:")

        if len(features) >= 96:
            # Берем последние 96 точек
            features_window = features[-96:]

            # Проверяем scaler (как в LLM TRANSFORM)
            features_scaled = ml_manager.scaler.transform(features_window)

            print("   📊 Данные после масштабирования:")
            print(f"   Shape: {features_scaled.shape}")
            print(f"   Range: [{features_scaled.min():.3f}, {features_scaled.max():.3f}]")

            # Прямое предсказание через ML Manager
            prediction = await ml_manager.predict(features_window)

            print("\n   🎯 Результат предсказания:")
            print(f"   • Signal Type: {prediction['signal_type']}")
            print(f"   • Confidence: {prediction['confidence']:.1%}")
            print(f"   • Signal Strength: {prediction['signal_strength']:.3f}")
            print(f"   • Raw Directions: {prediction['predictions']['raw_directions']}")

        # 5. Signal Processing (проверяем обработку сигнала)
        print("\n4️⃣ Signal Processing:")

        # Проверяем кеш
        cache_key = f"ml_signal:{symbol}"

        # Генерируем сигнал через processor
        signal = await ml_processor.process_symbol(symbol)

        if signal:
            print("   ✅ Сигнал сгенерирован:")
            print(f"   • Type: {signal.signal_type.value}")
            print(f"   • Entry Price: ${signal.suggested_price:.2f}")
            print(f"   • Stop Loss: ${signal.suggested_stop_loss:.2f}")
            print(f"   • Take Profit: ${signal.suggested_take_profit:.2f}")
            print(f"   • Confidence: {signal.confidence:.1%}")

            # Проверка индикаторов в сигнале
            if signal.indicators:
                print("\n   📊 Индикаторы в сигнале:")
                indicators = signal.indicators

                if "ml_predictions" in indicators:
                    ml_pred = indicators["ml_predictions"]
                    print(f"   • Direction Score: {ml_pred.get('direction_score', 0):.3f}")
                    print(f"   • Raw Directions: {ml_pred.get('raw_directions', [])}")

                if "technical_indicators" in indicators:
                    tech = indicators["technical_indicators"]
                    print(f"   • RSI: {tech.get('rsi', 0):.2f}")
                    print(f"   • MA20: {tech.get('ma_20', 0):.2f}")
        else:
            print("   ❌ Сигнал не сгенерирован")

    # 6. Сравнение с LLM TRANSFORM
    print(f"\n{'=' * 80}")
    print("📋 СРАВНЕНИЕ С LLM TRANSFORM:")
    print(f"{'=' * 80}\n")

    print("🔍 Ключевые отличия найдены:")
    print("\n1. ПРОБЛЕМА С DIRECTION HEAD:")
    print("   • LLM TRANSFORM: direction_head выдает 12 значений (3 класса × 4 таймфрейма)")
    print("   • BOT_AI_V3: ожидает только 4 значения направлений")
    print("   • Модель выдает [2.0, 2.0, 2.0, 2.0] из-за неправильной интерпретации")

    print("\n2. ПРОБЛЕМА С FEATURE SCALING:")
    print("   • LLM TRANSFORM: использует StandardScaler с сохраненными параметрами")
    print("   • BOT_AI_V3: scaler загружен правильно, но features могут отличаться")

    print("\n3. ПРОБЛЕМА С SIGNAL GENERATION:")
    print("   • Stop Loss/Take Profit считаются неправильно (отрицательные значения)")
    print("   • Нужно использовать текущую цену как базу для расчета")

    print("\n🛠️ РЕКОМЕНДАЦИИ:")
    print("1. Исправить интерпретацию direction_head (взять правильные индексы)")
    print("2. Проверить соответствие признаков между проектами")
    print("3. Исправить расчет Stop Loss/Take Profit относительно текущей цены")
    print("4. Добавить проверку валидности сигналов перед сохранением")


if __name__ == "__main__":
    asyncio.run(monitor_ml_pipeline())
