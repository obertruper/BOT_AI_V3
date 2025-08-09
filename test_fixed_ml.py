#!/usr/bin/env python3
"""
Тестирование исправленной интерпретации ML модели
"""

import asyncio
import sys

import pandas as pd

sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from core.logger import setup_logger
from database.connections.postgres import AsyncPGPool
from ml.ml_manager import MLManager
from ml.ml_signal_processor import MLSignalProcessor

logger = setup_logger("test_fixed_ml")


async def test_fixed_ml():
    """Тестирует исправленную интерпретацию ML модели."""

    print("🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕННОЙ ML ИНТЕРПРЕТАЦИИ\n")

    # 1. Инициализация
    config = {"ml": {"model": {"device": "cuda"}, "model_directory": "models/saved"}}

    ml_manager = MLManager(config)
    await ml_manager.initialize()

    # 2. Загрузка тестовых данных
    print("1️⃣ Загрузка тестовых данных...")

    query = """
    SELECT * FROM raw_market_data
    WHERE symbol = 'BTCUSDT'
    ORDER BY datetime DESC
    LIMIT 100
    """

    raw_data = await AsyncPGPool.fetch(query)

    # Преобразуем в DataFrame
    df_data = [dict(row) for row in raw_data]
    df = pd.DataFrame(df_data)

    # Конвертируем Decimal в float
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    df = df.sort_values("datetime")

    print(f"✅ Загружено {len(df)} свечей")
    print(f"   Последняя цена: ${df['close'].iloc[-1]:.2f}")

    # 3. Тестирование предсказаний
    print("\n2️⃣ Тестирование ML предсказаний...")

    prediction = await ml_manager.predict(df)

    print("\n📊 РЕЗУЛЬТАТЫ ПРЕДСКАЗАНИЯ:")
    print(f"   Signal Type: {prediction['signal_type']}")
    print(f"   Confidence: {prediction['confidence']:.1%}")
    print(f"   Signal Strength: {prediction['signal_strength']:.3f}")
    print(f"   Risk Level: {prediction['risk_level']}")

    if "predictions" in prediction:
        pred = prediction["predictions"]
        print("\n📈 Детали предсказаний:")
        print(f"   Directions by timeframe: {pred.get('directions_by_timeframe', [])}")
        print(f"   Direction score: {pred.get('direction_score', 0):.3f}")

        if "direction_probabilities" in pred:
            print("\n   Вероятности по таймфреймам:")
            for i, probs in enumerate(pred["direction_probabilities"]):
                print(
                    f"   Таймфрейм {i + 1}: SHORT={probs[0]:.3f}, NEUTRAL={probs[1]:.3f}, LONG={probs[2]:.3f}"
                )

    # 4. Проверка Stop Loss и Take Profit
    print("\n3️⃣ Проверка Stop Loss и Take Profit:")

    current_price = df["close"].iloc[-1]
    stop_loss_pct = prediction.get("stop_loss_pct")
    take_profit_pct = prediction.get("take_profit_pct")

    if stop_loss_pct is not None and take_profit_pct is not None:
        print(f"   Stop Loss %: {stop_loss_pct:.3%}")
        print(f"   Take Profit %: {take_profit_pct:.3%}")

        if prediction["signal_type"] == "LONG":
            sl_price = current_price * (1 - stop_loss_pct)
            tp_price = current_price * (1 + take_profit_pct)
        else:
            sl_price = current_price * (1 + stop_loss_pct)
            tp_price = current_price * (1 - take_profit_pct)

        print(f"\n   При текущей цене ${current_price:.2f}:")
        print(f"   Stop Loss: ${sl_price:.2f}")
        print(f"   Take Profit: ${tp_price:.2f}")

    # 5. Тестирование MLSignalProcessor
    print("\n4️⃣ Тестирование MLSignalProcessor...")

    ml_processor = MLSignalProcessor(ml_manager, config)

    # Имитируем вызов process_signal
    from ml.logic.feature_engineering import FeatureEngineer

    feature_engineer = FeatureEngineer(config)
    features = feature_engineer.create_features(df)

    if len(features) >= 96:
        features_window = features[-96:]

        # Создаем предсказание напрямую
        signal = await ml_processor._convert_predictions_to_signal(
            symbol="BTCUSDT", predictions=prediction, current_price=current_price
        )

        if signal:
            print("\n✅ Сигнал успешно создан:")
            print(f"   Type: {signal.signal_type.value}")
            print(f"   Confidence: {signal.confidence:.1%}")
            print(f"   Strength: {signal.strength:.3f}")
            print(f"   Stop Loss: ${signal.suggested_stop_loss:.2f}")
            print(f"   Take Profit: ${signal.suggested_take_profit:.2f}")
        else:
            print("\n❌ Сигнал не создан (возможно NEUTRAL)")

    # 6. Итоговая проверка
    print("\n5️⃣ ИТОГОВАЯ ПРОВЕРКА:")

    issues = []

    # Проверка разнообразия предсказаний
    if "directions_by_timeframe" in prediction.get("predictions", {}):
        directions = prediction["predictions"]["directions_by_timeframe"]
        if len(set(directions)) == 1:
            issues.append("⚠️  Все таймфреймы показывают одинаковое направление")
        else:
            print("✅ Разнообразие в предсказаниях по таймфреймам")

    # Проверка Stop Loss/Take Profit
    if stop_loss_pct is not None and stop_loss_pct > 0:
        print("✅ Stop Loss корректно рассчитан (положительный процент)")
    else:
        issues.append("⚠️  Проблема с расчетом Stop Loss")

    if take_profit_pct is not None and take_profit_pct > 0:
        print("✅ Take Profit корректно рассчитан (положительный процент)")
    else:
        issues.append("⚠️  Проблема с расчетом Take Profit")

    # Проверка уверенности
    if 0.2 <= prediction["confidence"] <= 0.8:
        print("✅ Уверенность в разумных пределах")
    else:
        issues.append(
            f"⚠️  Уверенность {prediction['confidence']:.1%} выглядит подозрительно"
        )

    if issues:
        print("\n🔍 Обнаружены проблемы:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n🎉 Все проверки пройдены успешно!")


if __name__ == "__main__":
    asyncio.run(test_fixed_ml())
