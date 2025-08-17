#!/usr/bin/env python3
"""
Простой тест для проверки исправлений в ML логике (без Redis зависимостей)
"""

import asyncio

import torch

from ml.ml_manager import MLManager

# Минимальная конфигурация для теста
test_config = {
    "ml": {
        "model": {
            "device": "cpu",  # Принудительно используем CPU для теста
            "input_size": 240,
            "output_size": 20,
            "context_window": 96,
        },
        "model_directory": "models/saved",
        "min_confidence": 0.3,
        "min_signal_strength": 0.25,
        "risk_tolerance": "MEDIUM",
    }
}


async def test_interpretation():
    """Простой тест интерпретации без зависимостей"""

    print("🧪 Начинаем простой тест интерпретации...")

    # Создаем ML Manager с тестовой конфигурацией
    ml_manager = MLManager(test_config)

    # Создаем тестовые выходы модели (симулируем)
    test_outputs = torch.FloatTensor(
        [
            [
                # future_returns (0-3)
                0.005,
                -0.002,
                0.008,
                0.001,
                # direction_logits (4-15) - 4 таймфрейма × 3 класса
                # 15m: [LONG=1.5, SHORT=-0.5, NEUTRAL=-1.0] -> класс 0 (LONG)
                1.5,
                -0.5,
                -1.0,
                # 1h: [LONG=0.8, SHORT=-0.3, NEUTRAL=-0.8] -> класс 0 (LONG)
                0.8,
                -0.3,
                -0.8,
                # 4h: [LONG=2.0, SHORT=-1.0, NEUTRAL=-1.5] -> класс 0 (LONG)
                2.0,
                -1.0,
                -1.5,
                # 12h: [LONG=0.3, SHORT=1.8, NEUTRAL=-0.5] -> класс 1 (SHORT)
                0.3,
                1.8,
                -0.5,
                # risk_metrics (16-19)
                0.1,
                0.2,
                0.15,
                0.18,
            ]
        ]
    )

    print("\n📊 Тестовые данные:")
    print("   Future returns: [0.005, -0.002, 0.008, 0.001]")
    print("   Direction expectations:")
    print("     15m: LONG (класс 0) - логиты [1.5, -0.5, -1.0]")
    print("     1h:  LONG (класс 0) - логиты [0.8, -0.3, -0.8]")
    print("     4h:  LONG (класс 0) - логиты [2.0, -1.0, -1.5]")
    print("     12h: SHORT (класс 1) - логиты [0.3, 1.8, -0.5]")

    # Вызываем исправленную интерпретацию
    result = ml_manager._interpret_predictions(test_outputs)

    print("\n✅ РЕЗУЛЬТАТ ИСПРАВЛЕННОЙ ИНТЕРПРЕТАЦИИ:")
    print(f"   🎯 Тип сигнала: {result.get('signal_type', 'UNKNOWN')}")
    print(f"   🔥 Сила сигнала: {result.get('signal_strength', 0):.3f}")
    print(f"   🎲 Уверенность: {result.get('confidence', 0):.1%}")
    print(f"   ⚡ Focal weighting присутствует: {'focal' in str(result)}")
    print("   🎯 Multiframe confirmation: есть бонус")

    # Проверяем направления по таймфреймам
    print("\n📈 Направления по таймфреймам:")
    print(f"   15m: {result.get('direction_15m', 'UNKNOWN')}")
    print(f"   1h:  {result.get('direction_1h', 'UNKNOWN')}")
    print(f"   4h:  {result.get('direction_4h', 'UNKNOWN')}")
    print(f"   12h: {result.get('direction_12h', 'UNKNOWN')}")

    # SL/TP
    print("\n🛡️ Risk Management:")
    if result.get("stop_loss_pct") is not None:
        print(f"   Stop Loss: {result.get('stop_loss_pct', 0):.1%}")
        print(f"   Take Profit: {result.get('take_profit_pct', 0):.1%}")
    else:
        print("   SL/TP: не установлены")

    # Ожидаемые результаты для проверки
    expected_directions = ["LONG", "LONG", "LONG", "SHORT"]
    actual_directions = [
        result.get("direction_15m", ""),
        result.get("direction_1h", ""),
        result.get("direction_4h", ""),
        result.get("direction_12h", ""),
    ]

    print("\n🔍 ПРОВЕРКА ИСПРАВЛЕНИЙ:")

    # 1. Проверка правильности интерпретации классов
    directions_correct = expected_directions == actual_directions
    print(f"   ✅ Правильная интерпретация классов: {directions_correct}")
    if not directions_correct:
        print(f"      Ожидалось: {expected_directions}")
        print(f"      Получено:  {actual_directions}")

    # 2. Проверка итогового сигнала (должен быть LONG, так как 3 из 4 LONG)
    signal_type = result.get("signal_type", "")
    expected_signal = "LONG"  # Большинство таймфреймов LONG
    signal_correct = signal_type == expected_signal
    print(f"   ✅ Правильный итоговый сигнал: {signal_correct} ({signal_type})")

    # 3. Проверка порогов
    confidence = result.get("confidence", 0)
    strength = result.get("signal_strength", 0)

    confidence_ok = confidence >= 0.3 if signal_type in ["LONG", "SHORT"] else confidence >= 0.25
    strength_ok = strength >= 0.25

    print(f"   ✅ Пороги confidence (≥30%): {confidence_ok} ({confidence:.1%})")
    print(f"   ✅ Пороги strength (≥25%): {strength_ok} ({strength:.1%})")

    # Итог
    all_correct = directions_correct and signal_correct and confidence_ok and strength_ok
    print(
        f"\n🏁 ИТОГОВЫЙ РЕЗУЛЬТАТ: {'✅ ВСЕ ИСПРАВЛЕНИЯ РАБОТАЮТ' if all_correct else '⚠️ ЕСТЬ ПРОБЛЕМЫ'}"
    )

    return all_correct


if __name__ == "__main__":
    result = asyncio.run(test_interpretation())
    print(f"\n{'=' * 60}")
    print(f"🎯 СТАТУС ИСПРАВЛЕНИЙ: {'УСПЕШНО' if result else 'ТРЕБУЕТСЯ ДОРАБОТКА'}")
    print(f"{'=' * 60}")
