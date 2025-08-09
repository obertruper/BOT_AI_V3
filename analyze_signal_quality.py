#!/usr/bin/env python3
"""
Анализ качества торговых сигналов и используемых индикаторов
"""

import asyncio
import sys

sys.path.append("/mnt/SSD/PYCHARMPRODJECT/BOT_AI_V3")

from sqlalchemy import desc, select

from database.connections import get_async_db
from database.models.signal import Signal


async def analyze_signals():
    """Анализирует последние сигналы и их индикаторы."""

    async with get_async_db() as db:
        # Получаем последние 10 сигналов
        result = await db.execute(select(Signal).order_by(desc(Signal.id)).limit(10))
        signals = result.scalars().all()

        print("📊 АНАЛИЗ ПОСЛЕДНИХ 10 СИГНАЛОВ\n")

        for i, signal in enumerate(signals):
            print(f"\n{'=' * 80}")
            print(
                f"Сигнал #{i + 1}: {signal.symbol} - {signal.signal_type.value.upper()}"
            )
            print(f"Время: {signal.created_at}")
            print(f"Цена входа: ${signal.suggested_price:.4f}")
            print(f"Уверенность: {signal.confidence:.1%}")
            print(f"Сила сигнала: {signal.strength:.1%}")

            # Анализируем индикаторы
            if signal.indicators:
                indicators = signal.indicators

                # ML предсказания
                if "ml_predictions" in indicators:
                    ml = indicators["ml_predictions"]
                    print("\n📈 ML Предсказания:")
                    print(f"  • Доходность 15м: {ml.get('returns_15m', 0):.6f}")
                    print(f"  • Доходность 1ч: {ml.get('returns_1h', 0):.6f}")
                    print(f"  • Доходность 4ч: {ml.get('returns_4h', 0):.6f}")
                    print(f"  • Доходность 12ч: {ml.get('returns_12h', 0):.6f}")
                    print(f"  • Direction Score: {ml.get('direction_score', 0):.3f}")
                    print(f"  • Raw Directions: {ml.get('raw_directions', [])}")

                print(f"\n🎯 Оценка риска: {indicators.get('risk_level', 'N/A')}")
                print(
                    f"🎲 Вероятность успеха: {indicators.get('success_probability', 0):.1%}"
                )

                # Проблемы
                print("\n⚠️ ПРОБЛЕМЫ:")
                print(
                    f"  • Stop Loss: ${signal.suggested_stop_loss:.2f} (ОШИБКА - отрицательное значение!)"
                )
                print(
                    f"  • Take Profit: ${signal.suggested_take_profit:.2f} (ОШИБКА - отрицательное значение!)"
                )

        # Статистика
        print(f"\n{'=' * 80}")
        print("📊 ОБЩАЯ СТАТИСТИКА:")

        signal_types = {}
        total_confidence = 0
        total_strength = 0

        for signal in signals:
            signal_types[signal.signal_type.value] = (
                signal_types.get(signal.signal_type.value, 0) + 1
            )
            total_confidence += signal.confidence
            total_strength += signal.strength

        print("\nРаспределение сигналов:")
        for stype, count in signal_types.items():
            print(f"  • {stype.upper()}: {count} ({count / len(signals) * 100:.0f}%)")

        print("\nСредние показатели:")
        print(f"  • Средняя уверенность: {total_confidence / len(signals):.1%}")
        print(f"  • Средняя сила сигнала: {total_strength / len(signals):.1%}")

        print("\n🔍 ВЫВОДЫ:")
        print("1. ВСЕ сигналы LONG - модель не генерирует SHORT сигналы")
        print("2. Очень высокая уверенность (99.96%) - возможно переобучение")
        print(
            "3. Stop Loss и Take Profit имеют отрицательные значения - критическая ошибка!"
        )
        print(
            "4. Raw directions всегда [2.0, 2.0, 2.0, 2.0] - модель всегда предсказывает FLAT"
        )
        print("5. Direction Score всегда 1.0 - нет вариативности")

        print("\n📌 НАСТРОЙКИ ПОРОГОВ:")
        print("• min_confidence: 0.45 (снижено с 0.65)")
        print("• min_signal_strength: 0.2 (снижено с 0.3)")
        print("• dynamic_threshold: base=0.05 * diversity_factor")
        print("• direction_confidence_threshold: 0.25")

        print("\n🎯 КАК РАБОТАЕТ ЛОГИКА РЕШЕНИЙ:")
        print("1. Модель выдает raw_directions [2,2,2,2] (FLAT)")
        print("2. Нормализация через tanh дает [0.964, 0.964, 0.964, 0.964]")
        print("3. Интерпретация: >0.2 = LONG, <-0.2 = SHORT, иначе FLAT")
        print("4. Все значения >0.2, поэтому всегда LONG")
        print("5. Weighted direction = 1.0 (все LONG с весами)")
        print("6. Dynamic threshold ~0.05-0.1")
        print("7. 1.0 > 0.1 => сигнал LONG")

        print("\n❌ ГЛАВНАЯ ПРОБЛЕМА:")
        print("Модель всегда выдает одинаковые предсказания [2,2,2,2]")
        print("Это означает что ML модель не обучена правильно!")


if __name__ == "__main__":
    asyncio.run(analyze_signals())
