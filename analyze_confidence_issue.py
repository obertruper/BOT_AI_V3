#!/usr/bin/env python3
"""Детальный анализ проблемы с одинаковыми confidence значениями"""

import asyncio

import numpy as np

from core.config.config_manager import ConfigManager
from data.data_loader import DataLoader
from ml.ml_manager import MLManager


async def analyze():
    """Анализ проблемы с confidence"""

    # Загружаем конфигурацию
    config_manager = ConfigManager()
    config = config_manager.get_config()

    # Инициализируем компоненты
    ml_manager = MLManager(config)
    await ml_manager.initialize()

    data_loader = DataLoader(config)

    print("=" * 80)
    print("ДЕТАЛЬНЫЙ АНАЛИЗ ПРОБЛЕМЫ С CONFIDENCE")
    print("=" * 80)

    # Анализируем несколько символов
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOTUSDT", "BNBUSDT"]

    confidence_values = []
    signal_strengths = []

    for symbol in symbols:
        print(f"\n📊 Анализ {symbol}:")
        print("-" * 40)

        try:
            # Загружаем данные
            data = await data_loader.get_latest_data(
                symbol=symbol, exchange="bybit", interval="15m", limit=200
            )

            if data is None or data.empty:
                print(f"  ❌ Нет данных для {symbol}")
                continue

            # Делаем предсказание
            prediction = await ml_manager.predict(data)

            if prediction:
                # Извлекаем значения
                signal_type = prediction.get("signal_type", "NEUTRAL")
                signal_strength = prediction.get("signal_strength", 0)
                confidence = prediction.get("confidence", 0)

                confidence_values.append(confidence)
                signal_strengths.append(signal_strength)

                print(f"  Signal Type: {signal_type}")
                print(f"  Signal Strength: {signal_strength:.6f}")
                print(f"  Confidence: {confidence:.6f}")

                # Анализируем компоненты confidence
                predictions = prediction.get("predictions", {})

                # Извлекаем future returns
                returns_15m = predictions.get("returns_15m", 0)
                returns_1h = predictions.get("returns_1h", 0)
                returns_4h = predictions.get("returns_4h", 0)
                returns_12h = predictions.get("returns_12h", 0)

                print(
                    f"  Returns: 15m={returns_15m:.4f}, 1h={returns_1h:.4f}, "
                    f"4h={returns_4h:.4f}, 12h={returns_12h:.4f}"
                )

                # Проверяем, близко ли к пороговому значению
                if abs(confidence - 0.60) < 0.001:
                    print("  ⚠️ CONFIDENCE ТОЧНО НА ПОРОГЕ 0.60!")
                elif abs(confidence - 0.60) < 0.01:
                    print("  ⚠️ Confidence очень близко к порогу 0.60")

                # Анализируем формулу
                # combined_confidence = signal_strength * 0.4 + model_confidence * 0.4 + (1.0 - avg_risk) * 0.2
                # Если confidence ≈ 0.60 и signal_strength варьируется,
                # то model_confidence должен компенсировать

                risk_component = 0.7  # Предполагаем средний риск
                estimated_model_conf = (
                    confidence - signal_strength * 0.4 - risk_component * 0.2
                ) / 0.4

                print(f"  Расчетная model_confidence: {estimated_model_conf:.6f}")

        except Exception as e:
            print(f"  Ошибка: {e}")

    # Статистический анализ
    print("\n" + "=" * 80)
    print("СТАТИСТИЧЕСКИЙ АНАЛИЗ:")
    print("-" * 40)

    if confidence_values:
        conf_array = np.array(confidence_values)
        strength_array = np.array(signal_strengths)

        print(f"Confidence значения: {confidence_values}")
        print(f"Signal Strength значения: {signal_strengths}")

        print("\nConfidence статистика:")
        print(f"  Среднее: {conf_array.mean():.6f}")
        print(f"  Стд. откл.: {conf_array.std():.6f}")
        print(f"  Мин: {conf_array.min():.6f}")
        print(f"  Макс: {conf_array.max():.6f}")

        print("\nSignal Strength статистика:")
        print(f"  Среднее: {strength_array.mean():.6f}")
        print(f"  Стд. откл.: {strength_array.std():.6f}")

        # Проверяем корреляцию
        if len(confidence_values) > 1:
            correlation = np.corrcoef(conf_array, strength_array)[0, 1]
            print(f"\nКорреляция между confidence и signal_strength: {correlation:.4f}")

        # Проверяем, все ли значения близки к 0.60
        near_threshold = np.abs(conf_array - 0.60) < 0.01
        pct_near_threshold = near_threshold.sum() / len(conf_array) * 100

        print(f"\n{pct_near_threshold:.1f}% значений confidence в пределах 0.01 от порога 0.60")

        if pct_near_threshold > 80:
            print("\n🚨 ПРОБЛЕМА ОБНАРУЖЕНА!")
            print("Большинство confidence значений сконцентрированы около порога 0.60")
            print("\nВОЗМОЖНЫЕ ПРИЧИНЫ:")
            print("1. Модель переобучена выдавать минимальное значение для прохождения порога")
            print("2. В коде есть явная корректировка confidence до порогового значения")
            print("3. Формула расчета confidence дает одинаковый результат для разных входов")
            print("\nРЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:")
            print("1. Проверить расчет confidence_scores в модели (строки 633-640 в ml_manager.py)")
            print("2. Проверить, не корректируется ли confidence после расчета")
            print(
                "3. Проанализировать обучение модели - возможно переобучение на пороговое значение"
            )

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(analyze())
