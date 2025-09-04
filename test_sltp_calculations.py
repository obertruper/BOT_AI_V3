#!/usr/bin/env python3
"""
Тест новых расчётов SL/TP
"""

import asyncio
import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).parent))

from database.models.base_models import SignalType
from ml.ml_signal_processor import MLSignalProcessor

# Тестовая конфигурация
test_config = {
    "enhanced_sltp": {
        "initial": {
            "stop_loss_percent_min": 1.0,  # 1%
            "stop_loss_percent_max": 2.0,  # 2%
            "take_profit_percent_min": 3.6,  # 3.6%
            "take_profit_percent_max": 6.0,  # 6%
        }
    },
    "trading": {
        "default_stop_loss_pct": 0.015,
        "default_take_profit_pct": 0.045,
        "risk_reward_ratio": 3.0,
    },
    "ml": {"filters": {"min_confidence": 0.30, "min_signal_strength": 0.30}},
}


class TestMLManager:
    """Заглушка для ML менеджера"""

    pass


async def test_sltp_calculations():
    """Тестирует расчёты SL/TP с новыми параметрами"""

    print("=" * 80)
    print("ТЕСТИРОВАНИЕ НОВЫХ РАСЧЁТОВ SL/TP")
    print("=" * 80)

    # Создаём процессор с тестовой конфигурацией
    ml_manager = TestMLManager()
    processor = MLSignalProcessor(ml_manager, test_config)

    # Тестовые сценарии
    test_cases = [
        {
            "name": "LONG с высокой вероятностью",
            "signal_type": SignalType.LONG,
            "current_price": 100000.0,
            "profit_probabilities": [0.8, 0.75, 0.7],
            "risk_metrics": [
                0.008,
                0.015,
                0.02,
                0.03,
            ],  # max_drawdown_1h, max_rally_1h, max_drawdown_4h, max_rally_4h
        },
        {
            "name": "LONG со средней вероятностью",
            "signal_type": SignalType.LONG,
            "current_price": 3500.0,
            "profit_probabilities": [0.6, 0.55, 0.5],
            "risk_metrics": [0.01, 0.02, 0.015, 0.025],
        },
        {
            "name": "SHORT с высокой вероятностью",
            "signal_type": SignalType.SHORT,
            "current_price": 150.0,
            "profit_probabilities": [0.75, 0.8, 0.7],
            "risk_metrics": [0.012, 0.018, 0.02, 0.035],
        },
        {
            "name": "SHORT с низкой вероятностью",
            "signal_type": SignalType.SHORT,
            "current_price": 50.0,
            "profit_probabilities": [0.4, 0.35, 0.3],
            "risk_metrics": [0.015, 0.01, 0.025, 0.02],
        },
    ]

    print("\nТестовые сценарии:")
    print("-" * 80)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}:")
        print(f"   Цена входа: ${test_case['current_price']:.2f}")
        print(f"   Вероятности: {test_case['profit_probabilities']}")
        print(f"   Средняя вероятность: {np.mean(test_case['profit_probabilities']):.1%}")

        # Вызываем метод расчёта риска для теста
        stop_loss, take_profit = await processor._calculate_risk_levels(
            test_case["signal_type"],
            test_case["current_price"],
            test_case["profit_probabilities"],
            test_case["risk_metrics"],
        )

        # Рассчитываем проценты
        if test_case["signal_type"] == SignalType.LONG:
            sl_pct = (test_case["current_price"] - stop_loss) / test_case["current_price"] * 100
            tp_pct = (take_profit - test_case["current_price"]) / test_case["current_price"] * 100
            print("\n   📈 LONG результаты:")
        else:
            sl_pct = (stop_loss - test_case["current_price"]) / test_case["current_price"] * 100
            tp_pct = (test_case["current_price"] - take_profit) / test_case["current_price"] * 100
            print("\n   📉 SHORT результаты:")

        print(f"   Stop Loss: ${stop_loss:.2f} ({sl_pct:.1f}%)")
        print(f"   Take Profit: ${take_profit:.2f} ({tp_pct:.1f}%)")

        # Проверка соответствия требованиям
        sl_ok = 1.0 <= sl_pct <= 2.0
        tp_ok = 3.6 <= tp_pct <= 6.0

        print("\n   Проверка требований:")
        print(f"   SL в диапазоне 1-2%: {'✅' if sl_ok else '❌'} ({sl_pct:.2f}%)")
        print(f"   TP в диапазоне 3.6-6%: {'✅' if tp_ok else '❌'} ({tp_pct:.2f}%)")

        # Risk/Reward ratio
        rr_ratio = tp_pct / sl_pct
        print(f"   Risk/Reward: 1:{rr_ratio:.1f}")

        print("-" * 40)

    print("\n" + "=" * 80)
    print("✨ ТЕСТ ЗАВЕРШЁН")
    print("=" * 80)

    # Дополнительный тест с граничными значениями
    print("\n\n📊 ТЕСТ ГРАНИЧНЫХ ЗНАЧЕНИЙ:")
    print("=" * 80)

    edge_cases = [
        {"name": "Минимальная волатильность", "risk_metrics": [0.001, 0.001, 0.001, 0.001]},
        {"name": "Максимальная волатильность", "risk_metrics": [0.05, 0.05, 0.05, 0.05]},
        {"name": "Асимметричная волатильность", "risk_metrics": [0.001, 0.05, 0.05, 0.001]},
    ]

    for edge_case in edge_cases:
        print(f"\n{edge_case['name']}:")

        for signal_type in [SignalType.LONG, SignalType.SHORT]:
            stop_loss, take_profit = await processor._calculate_risk_levels(
                signal_type, 1000.0, [0.5, 0.5, 0.5], edge_case["risk_metrics"]
            )

            if signal_type == SignalType.LONG:
                sl_pct = (1000.0 - stop_loss) / 1000.0 * 100
                tp_pct = (take_profit - 1000.0) / 1000.0 * 100
                print(f"  LONG: SL={sl_pct:.2f}%, TP={tp_pct:.2f}%")
            else:
                sl_pct = (stop_loss - 1000.0) / 1000.0 * 100
                tp_pct = (1000.0 - take_profit) / 1000.0 * 100
                print(f"  SHORT: SL={sl_pct:.2f}%, TP={tp_pct:.2f}%")


if __name__ == "__main__":
    asyncio.run(test_sltp_calculations())
