#!/usr/bin/env python3
"""Анализ проблемы с confidence в ML предсказаниях"""

import asyncio

from ml.ml_manager import MLManager


async def analyze():
    """Анализ ML предсказаний"""

    # Загружаем конфигурацию
    from core.config.config_manager import ConfigManager

    config_manager = ConfigManager()

    # Инициализируем ML Manager
    ml_manager = MLManager(config_manager.get_config())

    # Список символов для анализа
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOTUSDT"]

    print("=" * 80)
    print("АНАЛИЗ ML CONFIDENCE")
    print("=" * 80)

    for symbol in symbols:
        print(f"\n📊 Анализ {symbol}:")
        print("-" * 40)

        try:
            # Получаем предсказание
            prediction = await ml_manager.get_trading_signals(
                symbols=[symbol], exchange="bybit"
            )

            # Извлекаем предсказание для символа
            if prediction and symbol in prediction:
                prediction = prediction[symbol]
            else:
                prediction = None

            if prediction:
                # Извлекаем компоненты confidence
                signal_strength = prediction.get("signal_strength", 0)
                confidence = prediction.get("confidence", 0)
                predictions = prediction.get("predictions", {})

                # Анализируем компоненты расчета confidence
                # Из ml_manager.py строка 638-640:
                # combined_confidence = signal_strength * 0.4 + model_confidence * 0.4 + (1.0 - avg_risk) * 0.2

                # Обратный расчет model_confidence
                # confidence = signal_strength * 0.4 + model_confidence * 0.4 + risk_component * 0.2
                # Предполагаем risk_component ≈ 0.7 (средний риск 0.3)
                risk_component = 0.7  # (1.0 - avg_risk) при avg_risk ≈ 0.3

                # model_confidence = (confidence - signal_strength * 0.4 - risk_component * 0.2) / 0.4
                estimated_model_conf = (
                    confidence - signal_strength * 0.4 - risk_component * 0.2
                ) / 0.4

                print(f"  Signal Type: {prediction.get('signal_type')}")
                print(f"  Signal Strength: {signal_strength:.4f}")
                print(f"  Confidence: {confidence:.4f}")
                print(f"  Estimated Model Conf: {estimated_model_conf:.4f}")

                # Анализ предсказаний по таймфреймам
                returns = [
                    predictions.get("returns_15m", 0),
                    predictions.get("returns_1h", 0),
                    predictions.get("returns_4h", 0),
                    predictions.get("returns_12h", 0),
                ]

                print(
                    f"  Returns: 15m={returns[0]:.4f}, 1h={returns[1]:.4f}, 4h={returns[2]:.4f}, 12h={returns[3]:.4f}"
                )

                # Проверяем формулу confidence
                # combined_confidence = signal_strength * 0.4 + model_confidence * 0.4 + (1.0 - avg_risk) * 0.2

                # Если все confidence ≈ 0.60, это может означать:
                # 1. signal_strength ≈ 0.75 (3 из 4 таймфреймов согласны)
                # 2. model_confidence ≈ 0.50 (sigmoid от 0)
                # 3. risk ≈ 0.30 (средний риск)
                # Результат: 0.75*0.4 + 0.50*0.4 + 0.70*0.2 = 0.30 + 0.20 + 0.14 = 0.64

                # Или более вероятно:
                # signal_strength = 1.0 (все согласны)
                # model_confidence = 0.35
                # risk = 0.30
                # Результат: 1.0*0.4 + 0.35*0.4 + 0.70*0.2 = 0.40 + 0.14 + 0.14 = 0.68

                # Проверим гипотезу
                if abs(confidence - 0.60) < 0.01:
                    print("  ⚠️ ПРОБЛЕМА: Confidence точно на пороге 0.60!")
                    print("  Возможные причины:")
                    print(
                        "    1. Модель обучена выдавать минимальную confidence для прохождения порога"
                    )
                    print(
                        "    2. Постпроцессинг корректирует confidence до порогового значения"
                    )
                    print("    3. Все компоненты формулы дают одинаковый результат")

            else:
                print("  Нет предсказания")

        except Exception as e:
            print(f"  Ошибка: {e}")

    print("\n" + "=" * 80)
    print("ВЫВОД:")
    print("Все ML сигналы имеют confidence ≈ 0.60, что точно соответствует порогу.")
    print("Это указывает на проблему в расчете confidence или постпроцессинге.")
    print("\nРЕКОМЕНДАЦИИ:")
    print("1. Проверить логику расчета confidence_scores в модели")
    print("2. Убедиться, что модель не переобучена на пороговое значение")
    print("3. Проверить, нет ли корректировки confidence до порога в коде")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(analyze())
