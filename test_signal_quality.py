#!/usr/bin/env python3
"""
Тестирование Signal Quality Analyzer
Демонстрация работы с разными типами сигналов
"""

import numpy as np

from ml.logic.signal_quality_analyzer import SignalQualityAnalyzer


def test_signal_quality():
    """Тест анализатора качества сигналов"""

    print("🧪 Тестирование Signal Quality Analyzer\n")
    print("=" * 60)

    # Создаем анализатор с конфигурацией
    from pathlib import Path

    import yaml

    config_path = Path("config/ml/ml_config.yaml")
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    analyzer = SignalQualityAnalyzer(config)

    # Тестовые сценарии
    scenarios = [
        {
            "name": "📈 ОТЛИЧНЫЙ СИГНАЛ (3 LONG из 4)",
            "directions": np.array([0, 0, 0, 2]),  # 3 LONG, 1 NEUTRAL
            "confidences": np.array([0.75, 0.80, 0.85, 0.55]),
            "returns": np.array([0.015, 0.012, 0.018, 0.003]),
            "probs": [
                np.array([0.7, 0.2, 0.1]),  # 15m - уверенный LONG
                np.array([0.8, 0.15, 0.05]),  # 1h - уверенный LONG
                np.array([0.85, 0.1, 0.05]),  # 4h - очень уверенный LONG
                np.array([0.3, 0.3, 0.4]),  # 12h - слабый NEUTRAL
            ],
        },
        {
            "name": "📉 ХОРОШИЙ SHORT (3 SHORT из 4)",
            "directions": np.array([1, 1, 1, 0]),  # 3 SHORT, 1 LONG
            "confidences": np.array([0.70, 0.75, 0.72, 0.45]),
            "returns": np.array([-0.012, -0.015, -0.013, 0.002]),
            "probs": [
                np.array([0.15, 0.70, 0.15]),  # 15m - уверенный SHORT
                np.array([0.1, 0.75, 0.15]),  # 1h - уверенный SHORT
                np.array([0.12, 0.72, 0.16]),  # 4h - уверенный SHORT
                np.array([0.45, 0.35, 0.20]),  # 12h - слабый LONG
            ],
        },
        {
            "name": "⚠️ СЛАБЫЙ СИГНАЛ (разнонаправленные)",
            "directions": np.array([2, 1, 0, 0]),  # NEUTRAL, SHORT, 2 LONG
            "confidences": np.array([0.40, 0.45, 0.48, 0.42]),
            "returns": np.array([0.001, -0.003, 0.005, 0.004]),
            "probs": [
                np.array([0.32, 0.33, 0.35]),  # 15m - NEUTRAL (неуверенный)
                np.array([0.30, 0.45, 0.25]),  # 1h - слабый SHORT
                np.array([0.48, 0.27, 0.25]),  # 4h - слабый LONG
                np.array([0.42, 0.33, 0.25]),  # 12h - слабый LONG
            ],
        },
        {
            "name": "❌ ПЛОХОЙ СИГНАЛ (все разные)",
            "directions": np.array([0, 1, 2, 1]),  # LONG, SHORT, NEUTRAL, SHORT
            "confidences": np.array([0.35, 0.38, 0.33, 0.36]),
            "returns": np.array([0.002, -0.001, 0.0005, -0.0015]),
            "probs": [
                np.array([0.35, 0.33, 0.32]),  # 15m - очень слабый LONG
                np.array([0.32, 0.38, 0.30]),  # 1h - очень слабый SHORT
                np.array([0.32, 0.33, 0.35]),  # 4h - очень слабый NEUTRAL
                np.array([0.31, 0.36, 0.33]),  # 12h - очень слабый SHORT
            ],
        },
    ]

    # Тестируем каждый сценарий
    for i, scenario in enumerate(scenarios, 1):
        print(f"\nСценарий {i}: {scenario['name']}")
        print("-" * 60)

        # Анализируем сигнал
        result = analyzer.analyze_signal(
            directions=scenario["directions"],
            confidences=scenario["confidences"],
            returns=scenario["returns"],
            direction_probs=scenario["probs"],
        )

        # Выводим результаты
        print(f"📊 Качество сигнала: {result['quality_level']} ({result['quality_score']:.3f})")
        print(f"   - Согласованность: {result['agreement_score']:.3f}")
        print(f"   - Уверенность: {result['confidence_score']:.3f}")
        print(f"   - Доходность: {result['return_score']:.3f}")
        print(f"   - Консистентность: {result['consistency_score']:.3f}")

        print(f"\n📌 Рекомендация: {result['recommendation']['action']}")
        print(f"   Тип сигнала: {result['recommendation']['signal_type']}")
        print(
            f"   Размер позиции: {result['recommendation']['position_size_multiplier'] * 100:.0f}%"
        )

        print("\n📝 Причины:")
        for reason in result["recommendation"]["reasons"]:
            print(f"   {reason}")

        print("\n🎯 Детали таймфреймов:")
        details = result["details"]["timeframe_agreement"]
        print(
            f"   15m: {details['15m']}, 1h: {details['1h']}, 4h: {details['4h']}, 12h: {details['12h']}"
        )

        if "LONG_count" in details:
            print(
                f"   LONG: {details.get('LONG_count', 0)}, "
                f"SHORT: {details.get('SHORT_count', 0)}, "
                f"NEUTRAL: {details.get('NEUTRAL_count', 0)}"
            )

    # Выводим итоговую статистику
    print("\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 60)

    stats = analyzer.get_statistics()
    print(f"Всего проанализировано: {stats['total_analyzed']}")
    print(f"Высокое качество: {stats['high_quality']} ({stats.get('high_quality_pct', 0):.1f}%)")
    print(
        f"Среднее качество: {stats['medium_quality']} ({stats.get('medium_quality_pct', 0):.1f}%)"
    )
    print(f"Низкое качество: {stats['low_quality']} ({stats.get('low_quality_pct', 0):.1f}%)")
    print(f"Отклонено: {stats['rejected']} ({stats.get('rejected_pct', 0):.1f}%)")

    print("\n" + "=" * 60)
    print("✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
    print("=" * 60)

    # Рекомендации по настройке
    print("\n📋 РЕКОМЕНДАЦИИ ПО НАСТРОЙКЕ:")
    print("1. Для консервативной торговли:")
    print("   - Требовать минимум 3 согласных таймфрейма")
    print("   - Quality score >= 0.75")
    print("   - Торговать только EXCELLENT сигналы")

    print("\n2. Для умеренной торговли:")
    print("   - Требовать минимум 2 согласных таймфрейма")
    print("   - Quality score >= 0.60")
    print("   - Торговать EXCELLENT и GOOD сигналы")

    print("\n3. Для активной торговли:")
    print("   - Основываться на главном таймфрейме (4h)")
    print("   - Quality score >= 0.45")
    print("   - Торговать все кроме REJECT сигналов")


if __name__ == "__main__":
    test_signal_quality()
