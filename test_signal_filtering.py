#!/usr/bin/env python3
"""
Тест системы фильтрации сигналов
"""

import sys
from pathlib import Path

import numpy as np

sys.path.append(str(Path(__file__).parent))

import yaml

from ml.logic.signal_quality_analyzer import FilterStrategy, SignalQualityAnalyzer


def test_filtering_strategies():
    """Тестирует разные стратегии фильтрации"""

    # Загружаем конфигурацию напрямую
    with open("config/ml/ml_config.yaml") as f:
        config = yaml.safe_load(f)

    print("=" * 70)
    print("🚦 ТЕСТ СИСТЕМЫ ФИЛЬТРАЦИИ СИГНАЛОВ")
    print("=" * 70)

    # Тестовые сценарии
    test_cases = [
        {
            "name": "Сильный сигнал (все LONG, высокая уверенность)",
            "directions": np.array([0, 0, 0, 0]),  # Все LONG
            "probs": [
                np.array([0.8, 0.1, 0.1]),  # 15m - сильный LONG
                np.array([0.7, 0.2, 0.1]),  # 1h - сильный LONG
                np.array([0.75, 0.15, 0.1]),  # 4h - сильный LONG
                np.array([0.7, 0.2, 0.1]),  # 12h - сильный LONG
            ],
            "returns": np.array([0.003, 0.004, 0.005, 0.006]),
            "risks": np.array([0.01, 0.01, 0.02, 0.02]),
        },
        {
            "name": "Средний сигнал (большинство LONG, средняя уверенность)",
            "directions": np.array([0, 0, 2, 0]),  # 3 LONG, 1 NEUTRAL
            "probs": [
                np.array([0.5, 0.3, 0.2]),  # 15m - средний LONG
                np.array([0.45, 0.35, 0.2]),  # 1h - средний LONG
                np.array([0.3, 0.3, 0.4]),  # 4h - NEUTRAL
                np.array([0.5, 0.3, 0.2]),  # 12h - средний LONG
            ],
            "returns": np.array([0.001, 0.002, 0.002, 0.003]),
            "risks": np.array([0.02, 0.02, 0.03, 0.03]),
        },
        {
            "name": "Слабый сигнал (разнонаправленный, низкая уверенность)",
            "directions": np.array([0, 1, 2, 0]),  # Разные направления
            "probs": [
                np.array([0.35, 0.33, 0.32]),  # 15m - слабый LONG
                np.array([0.32, 0.35, 0.33]),  # 1h - слабый SHORT
                np.array([0.31, 0.32, 0.37]),  # 4h - слабый NEUTRAL
                np.array([0.36, 0.32, 0.32]),  # 12h - слабый LONG
            ],
            "returns": np.array([0.0005, 0.0008, 0.001, 0.0012]),
            "risks": np.array([0.03, 0.03, 0.04, 0.04]),
        },
        {
            "name": "Противоречивый сигнал (LONG vs SHORT)",
            "directions": np.array([0, 1, 0, 1]),  # Чередование LONG/SHORT
            "probs": [
                np.array([0.6, 0.3, 0.1]),  # 15m - LONG
                np.array([0.2, 0.7, 0.1]),  # 1h - SHORT
                np.array([0.6, 0.3, 0.1]),  # 4h - LONG
                np.array([0.2, 0.7, 0.1]),  # 12h - SHORT
            ],
            "returns": np.array([-0.001, 0.002, -0.002, 0.003]),
            "risks": np.array([0.05, 0.05, 0.06, 0.06]),
        },
    ]

    # Тестируем каждую стратегию
    for strategy_name in ["conservative", "moderate", "aggressive"]:
        print(f"\n{'='*70}")
        print(f"📋 Стратегия: {strategy_name.upper()}")
        print(f"{'='*70}")

        # Создаем анализатор с нужной стратегией
        analyzer = SignalQualityAnalyzer(config)
        analyzer.active_strategy = FilterStrategy(strategy_name)

        for test_case in test_cases:
            result = analyzer.analyze_signal_quality(
                test_case["directions"],
                test_case["probs"],
                test_case["returns"],
                test_case["risks"],
                weighted_direction=0.0,  # Не используется в новой версии
            )

            status = "✅ ПРОШЕЛ" if result.passed else "❌ ОТКЛОНЕН"
            print(f"\n{test_case['name']}:")
            print(f"  Статус: {status}")
            print(f"  Тип сигнала: {result.signal_type}")
            print(f"  Качество: {result.quality_metrics.quality_score:.3f}")
            print(f"  Согласованность: {result.quality_metrics.agreement_score:.3f}")
            print(f"  Уверенность: {result.quality_metrics.confidence_score:.3f}")

            if not result.passed and result.rejection_reasons:
                print("  Причины отклонения:")
                for reason in result.rejection_reasons:
                    print(f"    - {reason}")

    # Выводим итоговую статистику
    print("\n" + "=" * 70)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 70)

    print("\nРекомендации:")
    print("  • Conservative: для реальных денег, минимум ложных сигналов")
    print("  • Moderate: баланс между частотой и качеством")
    print("  • Aggressive: для тестирования, максимум сигналов")


if __name__ == "__main__":
    test_filtering_strategies()
